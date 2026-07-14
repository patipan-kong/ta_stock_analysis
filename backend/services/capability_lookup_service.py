"""capability_lookup_service.py — symbol -> CapabilityView lookup (M30.1).

Design: docs/implementation/M30_capability_safety_foundation_design.md §3.1.

The only new module in M30 that performs symbol -> AssetType -> definition
identification. Lookup only: no predicate is evaluated, no finding is
recorded, no policy decision is made — see capability_safety.py for the
pure predicates a caller applies to whatever this module returns. This
split is the direct implementation of D5 ("engines consume declarations,
never kinds"): this module identifies, once, in one place; every
downstream consumer receives only a CapabilityView (or a named refusal),
never an AssetType and never a symbol-to-kind mapping of its own.

Reuses, never reimplements (ADR-004):
  - services.registry_lookup.resolve_asset() for symbol -> AssetView
    resolution (including its existing TTL cache) — this module does not
    duplicate identity resolution.
  - services.asset_definitions.BindingResolver for AssetType -> CapabilityView
    resolution.

Never raises. An unresolved symbol, an asset_type with no canonical
definition, or a registry boot failure all collapse to an
UnresolvedCapability — mirroring registry_lookup.py's own
`AssetView | Unresolved` contract and the never-raise discipline
_consult_runtime_for_mint() / _consult_runtime_capabilities() already
established (M11/M12 shadow consultations).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Sequence, Union

from sqlalchemy.orm import Session

from services import registry_lookup
from services.asset_definitions import (
    BindingResolver,
    CapabilityView,
    DefinitionRegistry,
    DefinitionRegistryError,
    UnresolvedBindingError,
)

_log = logging.getLogger(__name__)

__all__ = [
    "UnresolvedCapability",
    "resolve_capability_view",
    "resolve_capability_views",
]


@dataclass(frozen=True)
class UnresolvedCapability:
    """The decisive, non-exceptional answer to "no CapabilityView for this
    symbol (yet)" — mirrors registry_lookup.Unresolved. `reason` names
    which step failed, without raising."""

    symbol: str
    reason: str


_REASON_UNKNOWN_ASSET = "no matching asset in the registry"
_REASON_NO_DEFINITION = "asset_type has no canonical Asset Definition"
_REASON_REGISTRY_BOOT_FAILED = "DefinitionRegistry failed to boot"


def resolve_capability_view(db: Session, symbol: str) -> Union[CapabilityView, UnresolvedCapability]:
    """Resolves one symbol to its governing CapabilityView. Lookup only —
    delegates to resolve_capability_views() so the single- and batch-symbol
    paths share one implementation (ADR-004)."""
    return resolve_capability_views(db, [symbol])[symbol]


def resolve_capability_views(
    db: Session, symbols: Sequence[str],
) -> Dict[str, Union[CapabilityView, UnresolvedCapability]]:
    """Batch form — resolves several symbols, building the DefinitionRegistry
    once for the whole call rather than once per symbol, following the same
    build-once discipline _consult_runtime_capabilities() already uses.
    Duplicate symbols collapse to one key, same as registry_lookup.resolve_many().
    """
    try:
        registry = DefinitionRegistry.build()
    except DefinitionRegistryError as exc:
        _log.warning("capability_lookup_service: DefinitionRegistry.build() failed: %s", exc)
        return {symbol: UnresolvedCapability(symbol=symbol, reason=_REASON_REGISTRY_BOOT_FAILED) for symbol in symbols}

    resolver = BindingResolver(registry)
    result: Dict[str, Union[CapabilityView, UnresolvedCapability]] = {}
    for symbol in symbols:
        asset = registry_lookup.resolve_asset(db, symbol)
        if isinstance(asset, registry_lookup.Unresolved):
            result[symbol] = UnresolvedCapability(symbol=symbol, reason=_REASON_UNKNOWN_ASSET)
            continue
        try:
            result[symbol] = resolver.resolve(asset.asset_type.value)
        except UnresolvedBindingError:
            result[symbol] = UnresolvedCapability(symbol=symbol, reason=_REASON_NO_DEFINITION)
    return result
