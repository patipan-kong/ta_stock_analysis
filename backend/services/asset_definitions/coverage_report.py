"""Runtime Coverage Report — Stage R1.5 tooling (M13 brief, "1. Runtime
Coverage Analysis").

Read-only reporting over the Asset Definition Runtime: for every AssetType
member, is a definition loaded, and if so what does it grant. This is
audit/tooling code, not an engine — it is the intended caller of
GovernanceProjection (the enumerable door; see governance.py's own
docstring: "trust surfaces, audit UIs, the registry admin API ... may
enumerate"), never CapabilityView. Nothing in this module makes a decision;
it only describes the runtime's current state for a human reader preparing
for Stage R2. See enforcement_decisions.py for the (hand-authored, not
derived) judgment calls about what to do with what this module reports.

Which R1 consumers (M11, M12) would notice a missing definition for a given
binding is itself a fact about those consumers' own source, not a guess:
`_CONSUMER_BINDINGS` below transcribes which bindings each consumer's own
`_consult_runtime_*()` function actually resolves — ledger_validator.py's
three consultations always resolve either "EQUITY" or the CASH numeraire
(fixed in code, M11); asset_registry.py's mint() consultation resolves
whatever AssetType the caller mints (M12), i.e. any of the nine. Like
library.py's PINNED_FINGERPRINTS, this cross-reference is hand-maintained
rather than recomputed by importing and executing each consumer — accepted
for the same reason: a report about behavior should describe the behavior,
not re-run it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from services.asset_definitions.registry import DefinitionRegistry
from services.asset_domain import AssetType

_CONSUMER_BINDINGS = {
    "asset_registry.mint() (M12)": frozenset(member.value for member in AssetType),
    "ledger_validator._consult_runtime_capabilities() (M11)": frozenset({
        AssetType.EQUITY.value,
        AssetType.CASH.value,
    }),
}


@dataclass(frozen=True)
class AssetTypeCoverage:
    """One AssetType member's runtime coverage. Fields beyond `binding` and
    `defined` are empty/None when `defined` is False — there is nothing to
    report for a binding the registry does not carry."""

    binding:                  str
    defined:                  bool
    version:                  Optional[str]
    source_document:          Optional[str]
    flows_granted:             Tuple[str, ...]
    event_families_granted:    Tuple[str, ...]
    permitted_relationships:   Tuple[str, ...]
    consumers_affected:        Tuple[str, ...]


@dataclass(frozen=True)
class CoverageReport:
    rows: Tuple[AssetTypeCoverage, ...]

    @property
    def defined_count(self) -> int:
        return sum(1 for row in self.rows if row.defined)

    @property
    def total_count(self) -> int:
        return len(self.rows)


def generate_coverage_report(registry: Optional[DefinitionRegistry] = None) -> CoverageReport:
    """Builds a fresh, boot-validated DefinitionRegistry unless one is
    supplied. Callers that want to exercise a broken-registry scenario pass
    their own (see test_asset_definitions_enforcement.py) rather than this
    function reaching for library.py's tamper trick itself — reporting code
    should not need to know how to break the thing it reports on."""
    if registry is None:
        registry = DefinitionRegistry.build()

    rows = []
    for member in AssetType:
        binding = member.value
        projection = registry.get(binding)
        defined = projection is not None

        consumers_affected = tuple(sorted(
            name for name, bindings in _CONSUMER_BINDINGS.items()
            if not defined and binding in bindings
        ))

        if projection is None:
            rows.append(AssetTypeCoverage(
                binding=binding, defined=False, version=None, source_document=None,
                flows_granted=(), event_families_granted=(), permitted_relationships=(),
                consumers_affected=consumers_affected,
            ))
            continue

        d = projection.as_dict()
        rows.append(AssetTypeCoverage(
            binding=binding,
            defined=True,
            version=d["version"],
            source_document=d["source_document"],
            flows_granted=tuple(d["flows_granted"]),
            event_families_granted=tuple(d["event_families_granted"]),
            permitted_relationships=tuple(d["existence"]["permitted_relationships"]),
            consumers_affected=consumers_affected,
        ))

    return CoverageReport(rows=tuple(rows))


def render_text(report: CoverageReport) -> str:
    """Human-readable table, the shape the M13 brief itself sketches under
    "Example output"."""
    lines = ["Asset Type Coverage", ""]
    width = max(len(row.binding) for row in report.rows)
    for row in report.rows:
        status = "defined" if row.defined else "missing"
        line = f"{row.binding.ljust(width)}   {status}"
        if row.consumers_affected:
            line += f"   (affects: {', '.join(row.consumers_affected)})"
        lines.append(line)
    lines.append("")
    lines.append(f"{report.defined_count}/{report.total_count} AssetType members have a definition.")
    return "\n".join(lines)
