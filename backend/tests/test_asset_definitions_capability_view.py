"""Structural ask-never-identify tests (M9 TDD Section 2.2, Section 4.2,
Section 4.3 point 1 "Structural"): CapabilityView must not expose a kind
name, a version, or any enumeration of its own grants. These tests assert
the absence directly, on the class, so an accidental future addition of
`.name`, `.version`, `.list_flows()`, etc. fails a test instead of merely
violating an unenforced convention.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.asset_definitions import BindingResolver, DefinitionRegistry
from services.asset_definitions.capability_view import CapabilityView


_FORBIDDEN_NAMES = (
    "name", "version", "binding", "kind", "definition",
    "list_flows", "list_event_families", "list_relationships",
    "flows", "event_families", "relationships", "grants",
    "is_a", "kind_of", "source_document",
)


def test_capability_view_exposes_no_identifying_or_enumerable_surface():
    public_members = {m for m in dir(CapabilityView) if not m.startswith("_")}
    leaked = public_members & set(_FORBIDDEN_NAMES)
    assert not leaked, f"CapabilityView leaks identifying/enumerable members: {leaked}"


def test_capability_view_repr_and_str_do_not_reveal_kind():
    resolver = BindingResolver(DefinitionRegistry.build())
    equity_view = resolver.resolve("EQUITY")
    cash_view = resolver.resolve("CASH")

    assert repr(equity_view) == repr(cash_view) == "<CapabilityView>"
    assert "EQUITY" not in repr(equity_view) and "Equity" not in repr(equity_view)
    assert "CASH" not in repr(cash_view) and "Cash" not in repr(cash_view)


def test_capability_view_has_no_public_attribute_dict_leak():
    # __slots__ means there is no __dict__ to accidentally introspect for
    # the underlying transcription's name/version.
    resolver = BindingResolver(DefinitionRegistry.build())
    view = resolver.resolve("EQUITY")
    assert not hasattr(view, "__dict__")


def test_capability_view_query_methods_take_an_explicit_word_not_an_enumeration():
    # discipline 2 ("require, never enumerate") made mechanical: every
    # membership-query method requires the caller to already know and name
    # the word it's asking about (an argument), never returns a collection.
    import inspect
    from services.asset_definitions.vocabulary import EventFamily, FlowType, RelationshipKind

    resolver = BindingResolver(DefinitionRegistry.build())
    view = resolver.resolve("EQUITY")

    for method_name in ("grants_flow", "grants_event_family", "permits_relationship", "relationship_mandatory"):
        method = getattr(view, method_name)
        params = [p for p in inspect.signature(method).parameters.values()]
        assert len(params) == 1, f"{method_name} must take exactly one word argument"

    assert isinstance(view.grants_flow(FlowType.DIVIDEND), bool)
    assert isinstance(view.grants_event_family(EventFamily.SPLIT), bool)
    assert isinstance(view.permits_relationship(RelationshipKind.WRAPS), bool)
