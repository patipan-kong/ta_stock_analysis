"""Asset Registry — findings persistence layer (Milestone M2).

Pure DB access only, mirroring the M1 asset_repository.py discipline: no
business rules here. In particular, resolve_finding never overwrites the
original observation fields (finding_type, subject/related asset,
identifier, detail, created_at) — it only sets the resolution fields.
RegistryFinding rows are never deleted by this module.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from models.registry_finding import RegistryFinding
from services.asset_domain import AssetId


def create_finding(
    db: Session,
    *,
    finding_type: str,
    subject_asset_id: AssetId,
    detail: str,
    related_asset_id: Optional[AssetId] = None,
    identifier_type: Optional[str] = None,
    identifier_value: Optional[str] = None,
    status: str = "OPEN",
) -> RegistryFinding:
    row = RegistryFinding(
        finding_type=finding_type,
        status=status,
        subject_asset_id=subject_asset_id,
        related_asset_id=related_asset_id,
        identifier_type=identifier_type,
        identifier_value=identifier_value,
        detail=detail,
    )
    db.add(row)
    db.flush()
    return row


def get_finding(db: Session, finding_id: int) -> Optional[RegistryFinding]:
    return db.query(RegistryFinding).filter(RegistryFinding.id == finding_id).one_or_none()


def list_findings(
    db: Session,
    *,
    subject_asset_id: Optional[AssetId] = None,
    status: Optional[str] = None,
) -> Sequence[RegistryFinding]:
    q = db.query(RegistryFinding)
    if subject_asset_id is not None:
        q = q.filter(RegistryFinding.subject_asset_id == subject_asset_id)
    if status is not None:
        q = q.filter(RegistryFinding.status == status)
    return q.order_by(RegistryFinding.created_at.asc()).all()


def resolve_finding(
    db: Session,
    finding: RegistryFinding,
    *,
    status: str,
    resolution: str,
    resolution_note: str,
    resolved_by: Optional[str] = None,
    resolved_at: Optional[datetime] = None,
) -> RegistryFinding:
    finding.status = status
    finding.resolution = resolution
    finding.resolution_note = resolution_note
    finding.resolved_by = resolved_by
    finding.resolved_at = resolved_at or datetime.utcnow()
    db.flush()
    return finding
