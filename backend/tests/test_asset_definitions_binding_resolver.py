"""BindingResolver (M9 TDD Section 2.3): resolve() returns a view or
refuses loudly and by name; resolve_numeraire() is the documented,
retirement-conditioned transitional special case for cash (Section 10.3 —
cash is a column, not a minted asset, until multi-currency mints instances).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from services.asset_definitions import (
    BindingResolver,
    DefinitionRegistry,
    NumeraireNotResolvedError,
    UnresolvedBindingError,
)
from services.asset_definitions.capability_view import CapabilityView
from services.asset_definitions.registry import DefinitionRegistry as _Registry
from services.asset_definitions.vocabulary import AcquisitionSemantics, FlowType


def _resolver():
    return BindingResolver(DefinitionRegistry.build())


def test_resolve_known_binding_returns_capability_view():
    view = _resolver().resolve("EQUITY")
    assert isinstance(view, CapabilityView)
    assert view.acquisition_semantics() == AcquisitionSemantics.VENUE_TRADED


def test_resolve_unknown_binding_refuses_loudly_never_defaults():
    # M22: FUND is now defined; BOND remains the still-undefined example.
    with pytest.raises(UnresolvedBindingError) as excinfo:
        _resolver().resolve("BOND")
    assert "BOND" in str(excinfo.value)


def test_resolve_never_returns_none_on_failure_only_raises():
    # D7: refuse, never a silent None/default view standing in for "unknown".
    with pytest.raises(UnresolvedBindingError):
        _resolver().resolve("COMPLETELY_MADE_UP_BINDING")


def test_resolve_numeraire_returns_cash_capabilities_without_an_asset():
    view = _resolver().resolve_numeraire()
    assert view.grants_flow(FlowType.INTEREST) is True
    assert view.acquisition_semantics() == AcquisitionSemantics.NOT_TRANSACTABLE


def test_resolve_numeraire_fails_named_if_cash_definition_absent():
    empty_registry = _Registry(ladders={})
    resolver = BindingResolver(empty_registry)
    with pytest.raises(NumeraireNotResolvedError):
        resolver.resolve_numeraire()


def test_resolver_never_exposes_the_registry_it_wraps_as_a_lookup_shortcut():
    # Resolution is the only door (Section 2.3) — a caller should not be
    # able to reach a GovernanceProjection through the resolver.
    resolver = _resolver()
    assert not hasattr(resolver, "get")
    assert not hasattr(resolver, "all")
