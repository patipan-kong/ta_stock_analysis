"""Asset Registry — canonical Asset model (Milestone M1).

Introduces the platform's canonical Asset identity without changing any
existing behavior. Nothing in the existing platform references these
tables yet (see docs/implementation/ASSET_REGISTRY_IMPLEMENTATION_PLAN.md
M1 Definition of Done). All four tables here are purely additive: no
existing table gains a foreign key to any of these, and no existing table
is altered.

Shares the declarative Base defined in models/database.py rather than
introducing a second metadata registry.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from models.database import Base


class Asset(Base):
    """The permanent identity tier (ASSET_REGISTRY.md Section 3).

    `id` IS the domain asset_id (see services/asset_domain.py:AssetId) —
    an opaque, permanent, never-reassigned, never-reused token. That it is
    implemented as an autoincrement integer is a persistence detail: no
    consumer may depend on it being sequential, orderable, or otherwise
    meaningful beyond equality.

    canonical_symbol vs display_symbol — the identity model is only
    unambiguous if this distinction is respected:
      - canonical_symbol is assigned exactly ONCE, at minting, and is never
        reassigned — including when the real-world ticker it was minted
        from later changes (rebrand, exchange-mandated rename, DR
        re-listing). It is a stable internal handle, not a live ticker
        mirror.
      - A real-world ticker change is an evidence-tier event: record a new
        AssetIdentifier row and update display_symbol. asset_id and
        canonical_symbol are untouched by such a change.
      - Anything rendering a symbol to a user must read display_symbol,
        never canonical_symbol.
    """

    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)

    # Permanent tier
    canonical_symbol = Column(String, nullable=False, unique=True, index=True)
    asset_type = Column(String, nullable=False)
    market = Column(String, nullable=False)
    exchange = Column(String, nullable=False)
    currency = Column(String, nullable=False)
    status = Column(String, nullable=False, default="ACTIVE")

    # Evidence-facing convenience field — mutable, tracks the real world.
    display_symbol = Column(String, nullable=True)

    # Universal fields (UNIVERSAL_ASSET_ARCHITECTURE.md Section 2)
    tradable = Column(Boolean, nullable=False, default=True)
    fractional_support = Column(Boolean, nullable=False, default=False)
    lot_size = Column(Integer, nullable=True)
    settlement_cycle = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    identifiers = relationship(
        "AssetIdentifier", back_populates="asset", cascade="all, delete-orphan",
    )
    classifications = relationship(
        "AssetClassification", back_populates="asset", cascade="all, delete-orphan",
    )


class AssetIdentifier(Base):
    """Evidence tier: external identifiers and provider symbols.

    Historical mappings are retained forever (ASSET_REGISTRY.md Section 3)
    — a superseded identifier row is never deleted, only has is_current
    flipped to False when a newer mapping is recorded.
    """

    __tablename__ = "asset_identifiers"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    identifier_type = Column(String, nullable=False)
    value = Column(String, nullable=False)
    source = Column(String, nullable=False)
    is_current = Column(Boolean, nullable=False, default=True)
    as_of = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    asset = relationship("Asset", back_populates="identifiers")

    __table_args__ = (
        UniqueConstraint(
            "asset_id", "identifier_type", "value",
            name="uq_asset_identifier_asset_type_value",
        ),
    )


class AssetRelationship(Base):
    """Mechanism linking listings that represent 'the same thing' in some
    sense (dual-listed, DR-of, successor-of, merged-into) without merging
    their records (ASSET_REGISTRY.md Section 5). The unit of identity
    remains the listing on each side of the relationship.
    """

    __tablename__ = "asset_relationships"

    id = Column(Integer, primary_key=True, index=True)
    from_asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    to_asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String, nullable=False)
    effective_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "from_asset_id", "to_asset_id", "relationship_type",
            name="uq_asset_relationship_from_to_type",
        ),
    )


class AssetClassification(Base):
    """Classification stewardship (ASSET_REGISTRY.md Section 8): dated,
    provenance-tagged business facts on a permanent identity spine.

    `value` is deliberately a plain string, NOT an enum-backed column —
    classification values (sector names, region names, ...) are
    registry-managed vocabulary that evolves independently of code (see
    services/asset_domain.py module docstring for the full rationale).
    Superseded facts are retained with is_current=False, never deleted.
    """

    __tablename__ = "asset_classifications"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    dimension = Column(String, nullable=False)
    value = Column(String, nullable=False)
    source = Column(String, nullable=False)
    is_current = Column(Boolean, nullable=False, default=True)
    as_of = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    asset = relationship("Asset", back_populates="classifications")
