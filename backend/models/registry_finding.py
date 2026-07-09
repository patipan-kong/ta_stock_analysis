"""Asset Registry — findings evidence (Milestone M2).

RegistryFinding is a durable evidence record, not an error log: it captures
something the Registry noticed about identity (a duplicate claim at mint
time, a conflicting identifier) that requires human or downstream
adjudication. A finding is never deleted and its original observation
(finding_type, subject/related asset, identifier, detail, created_at) is
never overwritten — resolving a finding only appends resolution fields
(status, resolution, resolution_note, resolved_by, resolved_at) on top of
the original record, preserving the full trail of what was observed and
what was later decided about it (ASSET_REGISTRY.md Section 7).

Purely additive: no existing table is altered, and no existing table gains
a foreign key to this one.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from models.database import Base


class RegistryFinding(Base):
    """A surfaced identity finding awaiting or having received adjudication.

    subject_asset_id is always populated — the asset the finding is about
    (the asset that already held a conflicting identifier, or the newly
    minted asset that shares history with another). related_asset_id is
    populated when a second asset is involved (the other side of a
    duplicate/conflict/merge); it is null for findings with no second party.
    """

    __tablename__ = "registry_findings"

    id = Column(Integer, primary_key=True, index=True)
    finding_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="OPEN", index=True)

    subject_asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    related_asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=True, index=True)

    identifier_type = Column(String, nullable=True)
    identifier_value = Column(String, nullable=True)

    detail = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Resolution fields — populated only when the finding is closed out.
    # Never used to overwrite the fields above; the original observation is
    # permanent evidence regardless of how it was later resolved.
    resolution = Column(String, nullable=True)
    resolution_note = Column(Text, nullable=True)
    resolved_by = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    subject_asset = relationship("Asset", foreign_keys=[subject_asset_id])
    related_asset = relationship("Asset", foreign_keys=[related_asset_id])
