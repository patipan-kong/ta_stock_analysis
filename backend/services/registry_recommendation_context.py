"""Asset Registry — Recommendation Write-Path Integration
(M6 Compatibility-Layer Integration, Phase 3).

Resolves every symbol in a recommendation's scores_map through the Registry
compatibility layer (services.registry_lookup.resolve_asset) and returns an
additive, JSON-serializable metadata dict per symbol. This module contains
zero identity rules of its own (ADR-004) — every fact returned here is
copied straight out of the AssetView / Unresolved values registry_lookup.py
already computes; nothing is re-derived or re-adjudicated.

Used exactly once, at the recommendation write path: main.py's
POST /analyze/optimizer, immediately before
services.decision_memory.snapshot_writer.write_recommendation_snapshot().
The enriched copy this module returns is what gets persisted into
RecommendationSnapshot.scores_map_json — the one free-form JSON column on
the Recommendation record that can carry additive metadata without a
schema change (no other column/table touched by this phase).

Deliberately does NOT mutate its input. The live `scores_map` dict at the
call site also feeds the AI prompt, portfolio_data/watchlist_data
construction, timing enrichment, and services.optimizer.execution_penalty —
none of that may change shape or content because of this integration
(OPTIMIZER_PHILOSOPHY.md Sec 6: identity resolution is arithmetic-side
bookkeeping and must never reach the AI's input). enrich_scores_map_for_
snapshot() therefore always returns a *new* dict; scores_map itself, and
everything already computed from it before this call, is untouched.

Fallback discipline (mandatory, per ASSET_REGISTRY.md Sec 4 "resolve
decisively or ask — never guess" and REGISTRY_INTEGRATION_GUIDE.md):
a symbol the Registry cannot resolve is recorded as resolved=False with a
reason, never omitted and never guessed. Any unexpected error resolving a
single symbol is caught per-symbol so one bad symbol cannot abort the
batch; any unexpected error building the batch itself is caught so
Recommendation generation continues exactly as it did before this module
existed, with the original scores_map (unenriched) persisted instead. This
module never raises.

Not covered by this phase (see docs/implementation/
M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md Section 5, Phase 3 status):
  - SignalHistory has no free-form JSON column, so it cannot carry
    asset_id without a schema change ("No schema migration is permitted"
    for this phase) — its rows remain symbol-only. Resolution for
    SignalHistory's symbols is still logged (this module is the single
    resolution pass shared by both), but not persisted.
  - Read-side consumers (plan_grader.read_snapshot_plan_inputs,
    optimizer_action_summary.build_action_summary) are unchanged — they
    already tolerate unknown keys in scores_map_json (they index specific
    fields like "current_price", never validate the full key set), so no
    read-side code needed to change for this write-side addition to be
    safe. Making them asset_id-aware is a distinct, later read-path step.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable

from sqlalchemy.orm import Session

from services import registry_lookup

log = logging.getLogger(__name__)

__all__ = ["build_registry_context", "enrich_scores_map_for_snapshot"]


def _view_to_dict(view: registry_lookup.AssetView) -> Dict[str, Any]:
    return {
        "resolved": True,
        "asset_id": int(view.asset_id),
        "canonical_symbol": view.canonical_symbol,
        "market": view.market,
        "exchange": view.exchange,
    }


def _unresolved_to_dict(reason: str) -> Dict[str, Any]:
    return {"resolved": False, "reason": reason}


def build_registry_context(db: Session, symbols: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    """Resolves every symbol in `symbols` and returns {symbol: registry_meta}.

    Never raises: an unexpected error resolving one symbol is caught and
    recorded as resolved=False with the error as its reason, rather than
    aborting the batch.
    """
    context: Dict[str, Dict[str, Any]] = {}
    resolved_count = 0

    for sym in dict.fromkeys(s for s in symbols if s):
        try:
            result = registry_lookup.resolve_asset(db, sym)
        except Exception as exc:
            log.debug(
                "registry_recommendation_context: resolve_asset raised for symbol=%r: %s",
                sym, exc,
            )
            context[sym] = _unresolved_to_dict(f"resolution error: {exc}")
            continue

        if isinstance(result, registry_lookup.AssetView):
            resolved_count += 1
            log.debug(
                "registry_recommendation_context: recommendation resolved symbol=%r "
                "asset_id=%s canonical_symbol used=%r",
                sym, int(result.asset_id), result.canonical_symbol,
            )
            context[sym] = _view_to_dict(result)
        else:
            log.debug(
                "registry_recommendation_context: recommendation unresolved symbol=%r "
                "reason=%r — fallback path taken",
                sym, result.reason,
            )
            context[sym] = _unresolved_to_dict(result.reason)

    log.info(
        "registry_recommendation_context: resolved %d/%d symbols for recommendation write path",
        resolved_count, len(context),
    )
    return context


def enrich_scores_map_for_snapshot(
    db: Session, scores_map: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Returns a NEW dict — same keys and values as `scores_map`, plus an
    additive "registry" key on each entry — for use only when persisting a
    RecommendationSnapshot. Never mutates `scores_map` itself.

    On any unexpected failure building the Registry context, logs a
    warning and returns `scores_map` unchanged: Recommendation generation
    must continue exactly as today regardless of Registry health.
    """
    try:
        context = build_registry_context(db, scores_map.keys())
    except Exception as exc:
        log.warning(
            "registry_recommendation_context: registry context build failed — "
            "persisting scores_map without registry metadata: %s",
            exc,
        )
        return scores_map

    return {
        sym: {**entry, "registry": context.get(sym, _unresolved_to_dict("not evaluated"))}
        for sym, entry in scores_map.items()
    }
