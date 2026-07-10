"""Asset Registry — SECTOR Classification Seed (Classification Consolidation).

One-time (re-runnable) seed that copies services/sector_taxonomy.py's static
maps into the Registry as SECTOR AssetClassification facts, for every symbol
that the Registry can already resolve to a minted Asset. This is what lets
main.py's _get_sector() find sector data in the Registry on its very first
lookup, rather than only after some other process happens to write it.

Never overwrites. Per ASSET_REGISTRY.md Section 8 ("Registry describes;
Portfolio Policy judges") and ADR-002 ("never silently compensate for or
overwrite an existing decision"), a symbol that already carries a *current*
SECTOR classification — from this seed's own prior run, or from any future
human/provider source — is left untouched. This module only fills gaps; it
never re-derives or corrects an existing fact. Re-running it after new
symbols have been minted into the Registry (e.g. by a future M5 Track B
backfill) safely seeds only the newly-resolvable, still-unclassified ones.

Reuses, never reimplements (ADR-004):
  - services.registry_lookup.resolve_asset() for symbol -> Asset resolution
    (the same TTL-cached path every other read-path consumer uses).
  - services.registry_service.get_classifications() / record_classification()
    for reading/writing the classification fact itself.
  - services.sector_taxonomy.static_sector_lookup() for the seed VALUE — the
    exact same function main.py's _get_sector() falls back to, so a seeded
    Registry fact and the pre-Registry fallback can never disagree.
  - services.data_fetcher.normalize_dr_symbol() for DR detection — the
    platform's one DR-identity primitive, not a local regex copy.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence, Tuple

from sqlalchemy.orm import Session

from services import registry_lookup, registry_service
from services.asset_domain import ClassificationDimension
from services.data_fetcher import normalize_dr_symbol
from services.sector_taxonomy import static_sector_lookup

__all__ = ["SeedOutcome", "SeedReport", "seed_sector_classification"]

_SEED_SOURCE = "seed:sector_taxonomy"

Outcome = Literal["seeded", "already_classified", "unresolved", "no_seed_data"]


@dataclass(frozen=True)
class SeedOutcome:
    symbol: str
    outcome: Outcome
    sector: str | None = None


@dataclass(frozen=True)
class SeedReport:
    dry_run: bool
    outcomes: Tuple[SeedOutcome, ...]

    def _count(self, outcome: Outcome) -> int:
        return sum(1 for o in self.outcomes if o.outcome == outcome)

    @property
    def seeded(self) -> int:
        return self._count("seeded")

    @property
    def already_classified(self) -> int:
        return self._count("already_classified")

    @property
    def unresolved(self) -> int:
        return self._count("unresolved")

    @property
    def no_seed_data(self) -> int:
        return self._count("no_seed_data")


def seed_sector_classification(
    db: Session, symbols: Sequence[str], *, dry_run: bool = True,
) -> SeedReport:
    """For every symbol in `symbols`: resolve it through the Registry: if
    resolved and not already carrying a current SECTOR classification, look
    up a seed value in sector_taxonomy's static maps and record it.

    Writes only `db.flush()` (via registry_service.record_classification),
    never `db.commit()` — the caller owns the transaction boundary, matching
    every other manage.py-invoked Registry writer in this codebase.

    `dry_run=True` (the default) performs zero writes; every eligible symbol
    is reported as if it would be seeded (sector value computed but not
    persisted), so a caller can preview the effect before committing.
    """
    outcomes: list[SeedOutcome] = []

    for symbol in symbols:
        resolved = registry_lookup.resolve_asset(db, symbol)
        if not isinstance(resolved, registry_lookup.AssetView):
            outcomes.append(SeedOutcome(symbol, "unresolved"))
            continue

        existing = registry_service.get_classifications(
            db, resolved.asset_id, dimension=ClassificationDimension.SECTOR, current_only=True,
        )
        if existing:
            outcomes.append(SeedOutcome(symbol, "already_classified", sector=existing[0].value))
            continue

        is_dr = normalize_dr_symbol(symbol) != symbol
        value = static_sector_lookup(symbol, is_dr=is_dr)
        if not value:
            outcomes.append(SeedOutcome(symbol, "no_seed_data"))
            continue

        if not dry_run:
            registry_service.record_classification(
                db, resolved.asset_id, ClassificationDimension.SECTOR, value, source=_SEED_SOURCE,
            )
            registry_lookup.invalidate_cache(symbol)
        outcomes.append(SeedOutcome(symbol, "seeded", sector=value))

    return SeedReport(dry_run=dry_run, outcomes=tuple(outcomes))
