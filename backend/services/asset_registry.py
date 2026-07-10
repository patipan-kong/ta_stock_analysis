"""Asset Registry — business rules (Milestone M1).

AssetRegistryService is the sole place lifecycle legality, identity
uniqueness, and classification/identifier stewardship rules are enforced.
services/asset_repository.py performs no validation of its own — this
module is the one authoritative implementation of those rules (ADR-004).

Nothing in the existing platform calls this service yet (M1 Definition of
Done). It exists as a self-contained foundation for later milestones.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, FrozenSet, Optional, Sequence

from sqlalchemy.orm import Session

from models.asset import Asset, AssetClassification, AssetIdentifier, AssetRelationship
from services import asset_repository as repo
from services.asset_domain import (
    AssetClaim,
    AssetId,
    AssetStatus,
    ClassificationDimension,
    IdentifierRecord,
    RelationshipType,
)

# Legal forward-only transitions out of each status (ASSET_REGISTRY.md
# Section 6). ARCHIVED is terminal. Minting always produces ACTIVE, never
# any of these states directly, so there is no entry for "pre-mint".
_ALLOWED_TRANSITIONS: Dict[AssetStatus, FrozenSet[AssetStatus]] = {
    AssetStatus.ACTIVE: frozenset({AssetStatus.SUSPENDED, AssetStatus.DELISTED, AssetStatus.MERGED}),
    AssetStatus.SUSPENDED: frozenset({AssetStatus.ACTIVE, AssetStatus.DELISTED}),
    AssetStatus.DELISTED: frozenset({AssetStatus.ARCHIVED}),
    AssetStatus.MERGED: frozenset({AssetStatus.ARCHIVED}),
    AssetStatus.ARCHIVED: frozenset(),
}


class AssetRegistryError(ValueError):
    """Raised when a Registry operation would violate an identity or
    lifecycle invariant. Never raised for ordinary not-found lookups —
    callers should check for None themselves in that case."""


def mint(db: Session, claim: AssetClaim, *, identifiers: Optional[Sequence[IdentifierRecord]] = None) -> Asset:
    """The one irreversible moment: creates a permanent asset_id and
    canonical_symbol from a pre-mint claim. Minting always produces status
    ACTIVE — ClaimStatus (Discovery/Candidate) is pre-mint vocabulary only
    and is not itself persisted.
    """
    if not claim.canonical_symbol or not claim.canonical_symbol.strip():
        raise AssetRegistryError("canonical_symbol must be non-empty")
    if not claim.market or not claim.exchange or not claim.currency:
        raise AssetRegistryError("market, exchange, and currency are required to mint an asset")

    existing = repo.get_asset_by_canonical_symbol(db, claim.canonical_symbol)
    if existing is not None:
        raise AssetRegistryError(
            f"canonical_symbol '{claim.canonical_symbol}' is already minted as asset_id={existing.id}; "
            "canonical_symbol is permanent and may never be reassigned"
        )

    row = repo.create_asset(
        db,
        canonical_symbol=claim.canonical_symbol,
        asset_type=claim.asset_type.value,
        market=claim.market,
        exchange=claim.exchange,
        currency=claim.currency,
        status=AssetStatus.ACTIVE.value,
        display_symbol=claim.display_symbol or claim.canonical_symbol,
        tradable=claim.tradable,
        fractional_support=claim.fractional_support,
        lot_size=claim.lot_size,
        settlement_cycle=claim.settlement_cycle,
    )

    for identifier in identifiers or ():
        attach_identifier(db, AssetId(row.id), identifier)

    return row


def get_asset(db: Session, asset_id: AssetId) -> Optional[Asset]:
    return repo.get_asset(db, asset_id)


def get_asset_by_canonical_symbol(db: Session, canonical_symbol: str) -> Optional[Asset]:
    return repo.get_asset_by_canonical_symbol(db, canonical_symbol)


def attach_identifier(db: Session, asset_id: AssetId, identifier: IdentifierRecord) -> AssetIdentifier:
    """Records an evidence-tier identifier. A real-world ticker/identifier
    change is expressed here — the prior current mapping for the same
    (asset_id, identifier_type) is superseded (is_current=False, retained
    forever), never edited or deleted, and the new mapping becomes current.

    Rejects attaching an identifier value that is already the CURRENT
    mapping for a different asset (conflicting identifiers, ASSET_REGISTRY.md
    Section 7) — the same real-world identifier cannot simultaneously
    point at two live assets.
    """
    asset = repo.get_asset(db, asset_id)
    if asset is None:
        raise AssetRegistryError(f"no asset with asset_id={asset_id}")

    conflict = repo.find_current_identifier(db, identifier.identifier_type.value, identifier.value)
    if conflict is not None and conflict.asset_id != asset_id:
        raise AssetRegistryError(
            f"identifier {identifier.identifier_type.value}:{identifier.value} is already the current "
            f"mapping for asset_id={conflict.asset_id}; cannot also attach it to asset_id={asset_id}"
        )
    if conflict is not None and conflict.asset_id == asset_id:
        return conflict  # already attached and current; idempotent

    current_same_type = [
        row for row in repo.get_identifiers(db, asset_id, current_only=True)
        if row.identifier_type == identifier.identifier_type.value
    ]
    for row in current_same_type:
        repo.mark_identifier_not_current(db, row)

    new_row = repo.add_identifier(
        db,
        asset_id=asset_id,
        identifier_type=identifier.identifier_type.value,
        value=identifier.value,
        source=identifier.source,
        as_of=identifier.as_of,
    )

    if identifier.identifier_type.value == "PROVIDER_SYMBOL":
        repo.update_display_symbol(db, asset, identifier.value)

    return new_row


def get_identifiers(db: Session, asset_id: AssetId, *, current_only: bool = False) -> Sequence[AssetIdentifier]:
    return repo.get_identifiers(db, asset_id, current_only=current_only)


def transition_status(db: Session, asset_id: AssetId, new_status: AssetStatus) -> Asset:
    """Enforces the forward-only lifecycle graph. asset_id is never reused
    and never un-minted regardless of the resulting status."""
    asset = repo.get_asset(db, asset_id)
    if asset is None:
        raise AssetRegistryError(f"no asset with asset_id={asset_id}")

    current_status = AssetStatus(asset.status)
    allowed = _ALLOWED_TRANSITIONS.get(current_status, frozenset())
    if new_status not in allowed:
        raise AssetRegistryError(
            f"illegal status transition for asset_id={asset_id}: "
            f"{current_status.value} -> {new_status.value}"
        )

    return repo.update_status(db, asset, new_status.value)


def link_relationship(
    db: Session,
    from_asset_id: AssetId,
    to_asset_id: AssetId,
    relationship_type: RelationshipType,
    *,
    effective_date: Optional[datetime] = None,
) -> AssetRelationship:
    """Links two listings without merging their records (ASSET_REGISTRY.md
    Section 5 — the unit of identity is the listing, not the entity)."""
    if from_asset_id == to_asset_id:
        raise AssetRegistryError("an asset cannot have a relationship to itself")
    if repo.get_asset(db, from_asset_id) is None:
        raise AssetRegistryError(f"no asset with asset_id={from_asset_id}")
    if repo.get_asset(db, to_asset_id) is None:
        raise AssetRegistryError(f"no asset with asset_id={to_asset_id}")

    for row in repo.get_relationships(db, from_asset_id):
        if (
            row.from_asset_id == from_asset_id
            and row.to_asset_id == to_asset_id
            and row.relationship_type == relationship_type.value
        ):
            return row  # idempotent

    return repo.add_relationship(
        db,
        from_asset_id=from_asset_id,
        to_asset_id=to_asset_id,
        relationship_type=relationship_type.value,
        effective_date=effective_date,
    )


def get_relationships(db: Session, asset_id: AssetId) -> Sequence[AssetRelationship]:
    return repo.get_relationships(db, asset_id)


def record_classification(
    db: Session,
    asset_id: AssetId,
    dimension: ClassificationDimension,
    value: str,
    source: str,
    *,
    as_of: Optional[datetime] = None,
) -> AssetClassification:
    """Records a dated, provenance-tagged classification fact
    (ASSET_REGISTRY.md Section 8). `value` is registry-managed vocabulary
    (a plain string), not an enum member — see services/asset_domain.py.
    Superseded facts are retained (is_current=False), never deleted.
    """
    if repo.get_asset(db, asset_id) is None:
        raise AssetRegistryError(f"no asset with asset_id={asset_id}")
    if not value or not value.strip():
        raise AssetRegistryError("classification value must be non-empty")

    current = [
        row for row in repo.get_classifications(db, asset_id, dimension=dimension.value, current_only=True)
    ]
    if current and current[0].value == value and current[0].source == source:
        return current[0]  # identical fact already current; idempotent

    for row in current:
        repo.mark_classification_not_current(db, row)

    return repo.add_classification(
        db,
        asset_id=asset_id,
        dimension=dimension.value,
        value=value,
        source=source,
        as_of=as_of,
    )


def get_classifications(
    db: Session, asset_id: AssetId, *, dimension: Optional[ClassificationDimension] = None, current_only: bool = False,
) -> Sequence[AssetClassification]:
    return repo.get_classifications(
        db, asset_id, dimension=dimension.value if dimension else None, current_only=current_only,
    )
