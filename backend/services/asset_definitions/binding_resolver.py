"""BindingResolver — from asset to view (M9 TDD Section 2.3).

Resolution is the only door engines get to a CapabilityView. The caller
gets a view or a named refusal — never a kind name, never a default.

R0 note (this milestone): nothing in the application calls this yet (M10
brief, Non-goals). It is built and tested standalone so the abstraction
exists, correct and proven, before any engine is asked to adopt it — the
"future abstraction replacing `if asset.type == ...`" the M10 brief
describes, still holstered.
"""
from __future__ import annotations

from typing import Optional

from services.asset_definitions.capability_view import CapabilityView
from services.asset_definitions.registry import DefinitionRegistry
from services.asset_domain import AssetType


class UnresolvedBindingError(Exception):
    """An asset is bound to a definition the registry does not carry.

    Per D7 (absence is a declaration, refuse loudly, never default): this
    is a named, loud refusal of one operation, never a boot failure (the
    defect is in one binding, not in the library — see registry.py for the
    boot-time checks) and never a fallback view.
    """


class NumeraireNotResolvedError(Exception):
    """The Cash definition itself is not loaded — a library defect, not a
    per-asset one. Distinct from UnresolvedBindingError so a caller (and a
    test) can tell "the registry is broken" apart from "this one asset's
    binding is bad."""


class BindingResolver:
    """Given a binding spelling and an as-of moment, returns the governing
    CapabilityView — or refuses. See module docstring."""

    def __init__(self, registry: DefinitionRegistry) -> None:
        self._registry = registry

    def resolve(self, binding: str, *, as_of: Optional[str] = None) -> CapabilityView:
        transcription = self._registry._resolve_transcription(binding, as_of=as_of)
        if transcription is None:
            raise UnresolvedBindingError(
                f"no definition admits binding '{binding}'"
                + (f" as of {as_of}" if as_of else "")
                + " — this asset cannot be resolved to a capability view"
            )
        return CapabilityView(transcription)

    def resolve_numeraire(self, *, as_of: Optional[str] = None) -> CapabilityView:
        """The transitional special entry documented in M9 TDD Section 2.3
        and named as a constitutional gap in Section 10.3: cash today is
        `Portfolio.cash_balance`, a column, not a minted asset — there is no
        instance to resolve() with a binding. Until multi-currency mints
        cash instances (the documented retirement condition), a caller that
        needs the numeraire's capabilities asks here instead of resolve().

        This method exists to make the special case visible and singular —
        one named method, not a binding-less call to resolve() that would
        look, to a future reader, like an ordinary asset lookup.
        """
        transcription = self._registry._resolve_transcription(AssetType.CASH.value, as_of=as_of)
        if transcription is None:
            raise NumeraireNotResolvedError(
                "the Cash definition is not loaded in this registry — the numeraire has no capability view"
            )
        return CapabilityView(transcription)
