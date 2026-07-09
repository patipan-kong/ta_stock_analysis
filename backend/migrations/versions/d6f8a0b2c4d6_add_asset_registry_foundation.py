"""add_asset_registry_foundation

Revision ID: d6f8a0b2c4d6
Revises: c5d7e9f1a3b5
Create Date: 2026-07-09

Asset Registry epic — Milestone M1 (Canonical Asset Model).

Adds 4 new, standalone tables that form the identity core of the Asset
Registry (docs/architecture/ASSET_REGISTRY.md):
  - assets                : permanent identity tier (asset_id, canonical_symbol)
  - asset_identifiers     : evidence tier — external/provider identifiers
  - asset_relationships   : links between listings (dual-listed, DR-of, ...)
  - asset_classifications : dated, provenance-tagged classification facts

Purely additive. No existing table is altered and no existing table gains
a foreign key to these tables — nothing in the platform references the
Asset Registry yet. See M1 Definition of Done in
docs/implementation/ASSET_REGISTRY_IMPLEMENTATION_PLAN.md.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d6f8a0b2c4d6"
down_revision: Union[str, Sequence[str], None] = "c5d7e9f1a3b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── assets ───────────────────────────────────────────────────────────────
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("canonical_symbol", sa.String(), nullable=False),
        sa.Column("asset_type", sa.String(), nullable=False),
        sa.Column("market", sa.String(), nullable=False),
        sa.Column("exchange", sa.String(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("display_symbol", sa.String(), nullable=True),
        sa.Column("tradable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("fractional_support", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("lot_size", sa.Integer(), nullable=True),
        sa.Column("settlement_cycle", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("canonical_symbol", name="uq_assets_canonical_symbol"),
    )
    op.create_index("ix_assets_canonical_symbol", "assets", ["canonical_symbol"])

    # ── asset_identifiers ────────────────────────────────────────────────────
    op.create_table(
        "asset_identifiers",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_type", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("as_of", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "asset_id", "identifier_type", "value",
            name="uq_asset_identifier_asset_type_value",
        ),
    )
    op.create_index("ix_asset_identifiers_asset_id", "asset_identifiers", ["asset_id"])
    op.create_index(
        "ix_asset_identifiers_type_value", "asset_identifiers", ["identifier_type", "value"],
    )

    # ── asset_relationships ──────────────────────────────────────────────────
    op.create_table(
        "asset_relationships",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("from_asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(), nullable=False),
        sa.Column("effective_date", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "from_asset_id", "to_asset_id", "relationship_type",
            name="uq_asset_relationship_from_to_type",
        ),
    )
    op.create_index("ix_asset_relationships_from", "asset_relationships", ["from_asset_id"])
    op.create_index("ix_asset_relationships_to", "asset_relationships", ["to_asset_id"])

    # ── asset_classifications ────────────────────────────────────────────────
    op.create_table(
        "asset_classifications",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dimension", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("as_of", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_asset_classifications_asset_id", "asset_classifications", ["asset_id"])
    op.create_index(
        "ix_asset_classifications_dimension", "asset_classifications", ["dimension"],
    )


def downgrade() -> None:
    op.drop_index("ix_asset_classifications_dimension", table_name="asset_classifications")
    op.drop_index("ix_asset_classifications_asset_id", table_name="asset_classifications")
    op.drop_table("asset_classifications")

    op.drop_index("ix_asset_relationships_to", table_name="asset_relationships")
    op.drop_index("ix_asset_relationships_from", table_name="asset_relationships")
    op.drop_table("asset_relationships")

    op.drop_index("ix_asset_identifiers_type_value", table_name="asset_identifiers")
    op.drop_index("ix_asset_identifiers_asset_id", table_name="asset_identifiers")
    op.drop_table("asset_identifiers")

    op.drop_index("ix_assets_canonical_symbol", table_name="assets")
    op.drop_table("assets")
