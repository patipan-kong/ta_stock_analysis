"""Asset Definition Runtime (Milestone M10, Runtime Stage R0).

The executable projection of the Asset Definition Library
(docs/definitions/asset_definition_library.md) per the design in
docs/implementation/M9_ASSET_DEFINITION_RUNTIME_TDD.md ("the M9 TDD").

The library remains authoritative. Nothing in this package creates truth —
every declaration below is a transcription of one row of a canonical
document's Capability Projection table, and the conformance tests in
backend/tests/test_asset_definitions_conformance.py assert the transcription
says exactly what the document says.

R0 scope (this milestone): the runtime exists, validates itself at boot, and
is fully testable. Nothing in the application consumes it yet — see M9 TDD
Section 9 (Migration Strategy) for the staged rollout that follows.

Public surface, mirroring the four runtime objects of M9 TDD Section 2:
  - DefinitionRegistry  -- the loaded, boot-validated library (Section 2.1)
  - CapabilityView      -- the anonymous engine-facing projection (2.2)
  - BindingResolver     -- asset binding -> CapabilityView (2.3)
  - GovernanceProjection -- the enumerable human/audit surface (2.4)
"""
from __future__ import annotations

from services.asset_definitions.binding_resolver import (
    BindingResolver,
    NumeraireNotResolvedError,
    UnresolvedBindingError,
)
from services.asset_definitions.capability_view import CapabilityView
from services.asset_definitions.governance import GovernanceProjection
from services.asset_definitions.registry import DefinitionRegistry, DefinitionRegistryError

__all__ = [
    "BindingResolver",
    "CapabilityView",
    "DefinitionRegistry",
    "DefinitionRegistryError",
    "GovernanceProjection",
    "NumeraireNotResolvedError",
    "UnresolvedBindingError",
]
