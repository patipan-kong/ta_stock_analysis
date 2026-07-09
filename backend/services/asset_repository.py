"""Asset Registry — persistence layer (Milestone M1).

Pure DB access only. No business rules, no validation, no lifecycle
legality checks — those belong to AssetRegistryService
(services/asset_registry.py). This module's job is limited to reading and
writing rows; it never decides whether an operation is allowed.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from models.asset import Asset, AssetClassification, AssetIdentifier, AssetRelationship
from services.asset_domain import AssetId


def create_asset(
    db: Session,
    *,
    canonical_symbol: str,
    asset_type: str,
    market: str,
    exchange: str,
    currency: str,
    status: str,
    display_symbol: Optional[str],
    tradable: bool,
    fractional_support: bool,
    lot_size: Optional[int],
    settlement_cycle: Optional[str],
) -> Asset:
    row = Asset(
        canonical_symbol=canonical_symbol,
        asset_type=asset_type,
        market=market,
        exchange=exchange,
        currency=currency,
        status=status,
        display_symbol=display_symbol,
        tradable=tradable,
        fractional_support=fractional_support,
        lot_size=lot_size,
        settlement_cycle=settlement_cycle,
    )
    db.add(row)
    db.flush()
    return row


def get_asset(db: Session, asset_id: AssetId) -> Optional[Asset]:
    return db.query(Asset).filter(Asset.id == asset_id).one_or_none()


def get_asset_by_canonical_symbol(db: Session, canonical_symbol: str) -> Optional[Asset]:
    return db.query(Asset).filter(Asset.canonical_symbol == canonical_symbol).one_or_none()


def find_current_identifier(
    db: Session, identifier_type: str, value: str,
) -> Optional[AssetIdentifier]:
    return (
        db.query(AssetIdentifier)
        .filter(
            AssetIdentifier.identifier_type == identifier_type,
            AssetIdentifier.value == value,
            AssetIdentifier.is_current.is_(True),
        )
        .one_or_none()
    )


def add_identifier(
    db: Session,
    *,
    asset_id: AssetId,
    identifier_type: str,
    value: str,
    source: str,
    as_of: Optional[datetime] = None,
) -> AssetIdentifier:
    row = AssetIdentifier(
        asset_id=asset_id,
        identifier_type=identifier_type,
        value=value,
        source=source,
        is_current=True,
        as_of=as_of,
    )
    db.add(row)
    db.flush()
    return row


def get_identifiers(
    db: Session, asset_id: AssetId, *, current_only: bool = False,
) -> Sequence[AssetIdentifier]:
    q = db.query(AssetIdentifier).filter(AssetIdentifier.asset_id == asset_id)
    if current_only:
        q = q.filter(AssetIdentifier.is_current.is_(True))
    return q.order_by(AssetIdentifier.created_at.asc()).all()


def mark_identifier_not_current(db: Session, identifier: AssetIdentifier) -> None:
    identifier.is_current = False
    db.flush()


def add_relationship(
    db: Session,
    *,
    from_asset_id: AssetId,
    to_asset_id: AssetId,
    relationship_type: str,
    effective_date: Optional[datetime] = None,
) -> AssetRelationship:
    row = AssetRelationship(
        from_asset_id=from_asset_id,
        to_asset_id=to_asset_id,
        relationship_type=relationship_type,
        effective_date=effective_date,
    )
    db.add(row)
    db.flush()
    return row


def get_relationships(db: Session, asset_id: AssetId) -> Sequence[AssetRelationship]:
    return (
        db.query(AssetRelationship)
        .filter(
            (AssetRelationship.from_asset_id == asset_id)
            | (AssetRelationship.to_asset_id == asset_id)
        )
        .order_by(AssetRelationship.created_at.asc())
        .all()
    )


def add_classification(
    db: Session,
    *,
    asset_id: AssetId,
    dimension: str,
    value: str,
    source: str,
    as_of: Optional[datetime] = None,
) -> AssetClassification:
    row = AssetClassification(
        asset_id=asset_id,
        dimension=dimension,
        value=value,
        source=source,
        is_current=True,
        as_of=as_of,
    )
    db.add(row)
    db.flush()
    return row


def get_classifications(
    db: Session, asset_id: AssetId, *, dimension: Optional[str] = None, current_only: bool = False,
) -> Sequence[AssetClassification]:
    q = db.query(AssetClassification).filter(AssetClassification.asset_id == asset_id)
    if dimension is not None:
        q = q.filter(AssetClassification.dimension == dimension)
    if current_only:
        q = q.filter(AssetClassification.is_current.is_(True))
    return q.order_by(AssetClassification.created_at.asc()).all()


def mark_classification_not_current(db: Session, classification: AssetClassification) -> None:
    classification.is_current = False
    db.flush()


def update_status(db: Session, asset: Asset, new_status: str) -> Asset:
    asset.status = new_status
    asset.updated_at = datetime.utcnow()
    db.flush()
    return asset


def update_display_symbol(db: Session, asset: Asset, new_display_symbol: str) -> Asset:
    asset.display_symbol = new_display_symbol
    asset.updated_at = datetime.utcnow()
    db.flush()
    return asset
