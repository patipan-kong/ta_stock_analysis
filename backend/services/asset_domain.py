"""Asset Registry — domain vocabulary (Milestone M1).

Defines the structural, code-relevant concepts of asset identity per
docs/architecture/ASSET_REGISTRY.md and docs/architecture/UNIVERSAL_ASSET_ARCHITECTURE.md.

Identity model — read before touching canonical_symbol or display_symbol:
    asset_id is the permanent, opaque identity token (see AssetId below).
    canonical_symbol is assigned exactly once, at minting, and is NEVER
    reassigned — including when the real-world ticker it was minted from
    later changes (company rebrand, exchange-mandated rename, DR re-listing).
    A real-world ticker change is an evidence-tier event: a new
    AssetIdentifier row is recorded and display_symbol is updated to the new
    current-facing symbol. asset_id and canonical_symbol are untouched.
    Consumers needing "what to show the user right now" must read
    display_symbol, never canonical_symbol. canonical_symbol is a stable
    internal handle, not a live ticker mirror.

Vocabulary split (see PR discussion in ASSET_REGISTRY_IMPLEMENTATION_PLAN.md
M1 notes for the full rationale):
  - Structural concepts below (AssetType, AssetStatus, IdentifierType,
    RelationshipType, ClassificationDimension) are compile-time enums.
    They are small, closed sets that engines branch on or that define the
    lifecycle state machine itself — adding a new one is a genuine
    engineering event elsewhere in the platform, so gating it behind a code
    change is correct.
  - Classification VALUES (e.g. "Technology", a Thai SET sector name) are
    deliberately NOT enums. They are registry-managed vocabulary — dated,
    provenance-tagged business content per ASSET_REGISTRY.md Section 8 —
    and are validated at the service layer, not the type system.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import NewType, Optional

# The domain identity of an Asset. Implemented today as an autoincrement
# integer primary key (see models/asset.py), but that is a persistence
# detail, not the contract: nothing outside the repository's insert path
# may construct an AssetId, and nothing may rely on it being sequential,
# orderable, or otherwise meaningful beyond equality/lookup.
AssetId = NewType("AssetId", int)


class AssetType(str, Enum):
    """Structural type. Engines are expected to branch on this (per the
    Universal Asset Model's own test in UNIVERSAL_ASSET_ARCHITECTURE.md
    Section 2: "does the engine need to branch on this to do its job?")."""

    EQUITY = "EQUITY"
    ETF = "ETF"
    FUND = "FUND"
    BOND = "BOND"
    CRYPTO = "CRYPTO"
    COMMODITY = "COMMODITY"
    CASH = "CASH"
    PROPERTY = "PROPERTY"
    OTHER = "OTHER"


class AssetStatus(str, Enum):
    """Post-mint lifecycle status per ASSET_REGISTRY.md Section 6.

    Forward-only on a permanent identity. Legal transitions are enforced by
    AssetRegistryService.transition_status(), not by this enum alone:
      ACTIVE -> SUSPENDED -> ACTIVE (suspension is reversible)
      ACTIVE -> DELISTED -> ARCHIVED
      ACTIVE -> MERGED (terminal; see AssetRelationship for the successor)
      DELISTED / MERGED -> ARCHIVED (terminal)
    asset_id is never reused and never un-minted regardless of status.
    """

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DELISTED = "DELISTED"
    MERGED = "MERGED"
    ARCHIVED = "ARCHIVED"


class ClaimStatus(str, Enum):
    """Pre-mint claim vocabulary. Not persisted in M1 — no producer of
    claims exists until the Symbol Resolver (M3). Kept here only so the
    vocabulary is named and AssetClaim below has a status to carry."""

    DISCOVERY = "DISCOVERY"
    CANDIDATE = "CANDIDATE"


class IdentifierType(str, Enum):
    """Evidence-tier identifier schemes. A small, closed set of real-world
    standards that change on the order of decades, not sprints."""

    ISIN = "ISIN"
    CUSIP = "CUSIP"
    SEDOL = "SEDOL"
    FIGI = "FIGI"
    PROVIDER_SYMBOL = "PROVIDER_SYMBOL"
    BROKER_CODE = "BROKER_CODE"


class RelationshipType(str, Enum):
    """Mechanism for expressing sameness/succession across listings per
    ASSET_REGISTRY.md Section 5. The unit of identity is the listing;
    relationships link listings without merging their records."""

    DUAL_LISTED = "DUAL_LISTED"
    DEPOSITARY_RECEIPT_OF = "DEPOSITARY_RECEIPT_OF"
    CROSS_LISTED = "CROSS_LISTED"
    SUCCESSOR_OF = "SUCCESSOR_OF"
    MERGED_INTO = "MERGED_INTO"


class ClassificationDimension(str, Enum):
    """The axis a classification fact is asserted on. The dimension names
    are structural (fixed, small); the VALUES asserted under a dimension
    are registry-managed strings, not enum members (see module docstring)."""

    SECTOR = "SECTOR"
    REGION = "REGION"
    ASSET_CLASS = "ASSET_CLASS"


@dataclass(frozen=True)
class AssetClaim:
    """Unpersisted input to AssetRegistryService.mint().

    Represents a pre-mint claim (Discovery/Candidate per ASSET_REGISTRY.md
    Section 6). Nothing produces these yet — no Symbol Resolver exists
    until M3 — so this is a plain in-memory value object, not a table.
    """

    canonical_symbol: str
    asset_type: AssetType
    market: str
    exchange: str
    currency: str
    status: ClaimStatus = ClaimStatus.CANDIDATE
    display_symbol: Optional[str] = None
    tradable: bool = True
    fractional_support: bool = False
    lot_size: Optional[int] = None
    settlement_cycle: Optional[str] = None


@dataclass(frozen=True)
class IdentifierRecord:
    """Value object describing one evidence-tier identifier to attach."""

    identifier_type: IdentifierType
    value: str
    source: str
    as_of: Optional[datetime] = None
