"""Asset Registry — service boundary (Milestone M2).

The one internal entry point through which identity questions are asked
and identity verdicts are entered (ASSET_REGISTRY.md Section 7,
ASSET_REGISTRY_IMPLEMENTATION_PLAN.md M2). Nothing outside the Registry
consumes this yet — M2 exists in parallel with the rest of the platform,
which continues to use symbols directly (M2 Backward Compatibility note).

Every lifecycle/identifier/classification/relationship rule already has its
one authoritative implementation in services/asset_registry.py (M1, ADR-004
— one implementation per rule). This module never reimplements those rules;
it delegates to them and adds only the genuinely new M2 capabilities:
historical-aware lookup, findings-backed duplicate/conflict detection, an
explicit merge-recording operation, and a minimal findings adjudication
surface. M1's asset_registry.py, asset_repository.py, and asset_domain.py
are not modified by this milestone.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Sequence

from sqlalchemy.orm import Session

from models.asset import Asset, AssetClassification, AssetIdentifier, AssetRelationship
from models.registry_finding import RegistryFinding
from services import asset_registry as core
from services import registry_findings_repository as findings_repo
from services import registry_query as query
from services.asset_domain import (
    AssetClaim,
    AssetId,
    AssetStatus,
    ClassificationDimension,
    IdentifierRecord,
    IdentifierType,
    RelationshipType,
)
from services.asset_registry import AssetRegistryError
from services.registry_domain import FindingResolution, FindingStatus, FindingType

__all__ = [
    "AssetRegistryError",
    "mint_asset",
    "get_asset",
    "find_by_identifier",
    "attach_identifier",
    "supersede_identifier",
    "get_identifiers",
    "transition_status",
    "link_relationship",
    "get_relationships",
    "record_classification",
    "get_classifications",
    "record_merge",
    "list_open_findings",
    "resolve_finding",
    "get_asset_detail",
]


@dataclass(frozen=True)
class AssetDetail:
    """Internal read model for get_asset_detail(). NOT a public contract:
    this milestone has no consumers yet (M2 is in-process/internal only,
    per the Backward Compatibility note), so this shape is free to change
    without notice in a later milestone. Do not serialize this directly
    across a process boundary or treat its field set as stable API."""

    asset: Asset
    current_identifiers: Sequence[AssetIdentifier]
    current_classifications: Sequence[AssetClassification]
    relationships: Sequence[AssetRelationship]


# ── Identity: minting and lookup ────────────────────────────────────────────

def mint_asset(
    db: Session, claim: AssetClaim, *, identifiers: Optional[Sequence[IdentifierRecord]] = None,
) -> Asset:
    """Wraps core.mint() with pre-mint duplicate detection across the full
    identifier history (current + superseded), per ASSET_REGISTRY.md
    Section 7's duplicate-detection requirement.

    - An identifier that is a *current* mapping on another asset blocks the
      mint outright and records an OPEN DUPLICATE_CLAIM finding against the
      existing asset — the same real-world identifier cannot legitimately
      back two live claims.
    - An identifier that only matches *historically* does not block minting
      (identifier reuse over long time horizons is legitimate), but records
      an OPEN DUPLICATE_CLAIM finding on the new asset so a human can
      confirm this is intentional reuse rather than a resolver mistake.
    """
    # Pre-mint check: since minting hasn't happened yet, every row found
    # here necessarily belongs to some other, already-existing asset.
    prior_rows_by_identifier = [
        (identifier, query.find_identifier_rows(db, identifier.identifier_type.value, identifier.value))
        for identifier in identifiers or ()
    ]

    for identifier, rows in prior_rows_by_identifier:
        current_row = next((r for r in rows if r.is_current), None)
        if current_row is not None:
            findings_repo.create_finding(
                db,
                finding_type=FindingType.DUPLICATE_CLAIM.value,
                subject_asset_id=AssetId(current_row.asset_id),
                identifier_type=identifier.identifier_type.value,
                identifier_value=identifier.value,
                detail=(
                    f"Mint blocked for canonical_symbol='{claim.canonical_symbol}': incoming claim "
                    f"included identifier {identifier.identifier_type.value}:{identifier.value}, "
                    f"already the current mapping for asset_id={current_row.asset_id}"
                ),
            )
            raise AssetRegistryError(
                f"identifier {identifier.identifier_type.value}:{identifier.value} is already the "
                f"current mapping for asset_id={current_row.asset_id}; refusing to mint a new asset "
                "with a conflicting live identifier"
            )

    row = core.mint(db, claim, identifiers=identifiers)

    for identifier, rows in prior_rows_by_identifier:
        historical_asset_id = next((r.asset_id for r in rows if not r.is_current), None)
        if historical_asset_id is not None:
            findings_repo.create_finding(
                db,
                finding_type=FindingType.DUPLICATE_CLAIM.value,
                subject_asset_id=AssetId(row.id),
                related_asset_id=AssetId(historical_asset_id),
                identifier_type=identifier.identifier_type.value,
                identifier_value=identifier.value,
                detail=(
                    f"New asset_id={row.id} (canonical_symbol='{row.canonical_symbol}') was minted with "
                    f"identifier {identifier.identifier_type.value}:{identifier.value}, previously used "
                    f"(historically, not currently) by asset_id={historical_asset_id}. Possible "
                    "identifier reuse — confirm this is a distinct instrument."
                ),
            )

    return row


def get_asset(db: Session, asset_id: AssetId) -> Optional[Asset]:
    return core.get_asset(db, asset_id)


def find_by_identifier(db: Session, identifier_type: IdentifierType, value: str) -> List[Asset]:
    """Resolves an identifier to every asset that has ever claimed it,
    current or historical. May return more than one asset if the value has
    been legitimately reused over time — callers must not assume a single
    answer (ASSET_REGISTRY.md Section 2)."""
    rows = query.find_identifier_rows(db, identifier_type.value, value)
    seen: List[int] = []
    assets: List[Asset] = []
    for row in rows:
        if row.asset_id in seen:
            continue
        seen.append(row.asset_id)
        asset = core.get_asset(db, AssetId(row.asset_id))
        if asset is not None:
            assets.append(asset)
    return assets


# ── Identifiers ──────────────────────────────────────────────────────────────

def attach_identifier(db: Session, asset_id: AssetId, identifier: IdentifierRecord) -> AssetIdentifier:
    """Delegates to core.attach_identifier(). On a conflict, additionally
    records an OPEN IDENTIFIER_CONFLICT finding with both sides' provenance
    before re-raising — the conflict is never allowed to vanish as just a
    transient exception (ASSET_REGISTRY.md Section 7)."""
    try:
        return core.attach_identifier(db, asset_id, identifier)
    except AssetRegistryError as exc:
        conflict = next(
            (a for a in find_by_identifier(db, identifier.identifier_type, identifier.value) if a.id != asset_id),
            None,
        )
        findings_repo.create_finding(
            db,
            finding_type=FindingType.IDENTIFIER_CONFLICT.value,
            subject_asset_id=asset_id,
            related_asset_id=AssetId(conflict.id) if conflict is not None else None,
            identifier_type=identifier.identifier_type.value,
            identifier_value=identifier.value,
            detail=str(exc),
        )
        raise


def supersede_identifier(db: Session, asset_id: AssetId, identifier: IdentifierRecord) -> AssetIdentifier:
    """Explicit vocabulary for a real-world identifier change (rename,
    rebrand, re-listing). Identical behavior to attach_identifier — core
    already treats a new (asset_id, identifier_type) mapping as superseding
    the prior current one — this is a named entry point, not new logic."""
    return attach_identifier(db, asset_id, identifier)


def get_identifiers(db: Session, asset_id: AssetId, *, current_only: bool = False) -> Sequence[AssetIdentifier]:
    return core.get_identifiers(db, asset_id, current_only=current_only)


# ── Lifecycle ────────────────────────────────────────────────────────────────

def transition_status(db: Session, asset_id: AssetId, new_status: AssetStatus) -> Asset:
    return core.transition_status(db, asset_id, new_status)


# ── Relationships ────────────────────────────────────────────────────────────

def link_relationship(
    db: Session,
    from_asset_id: AssetId,
    to_asset_id: AssetId,
    relationship_type: RelationshipType,
    *,
    effective_date: Optional[datetime] = None,
) -> AssetRelationship:
    return core.link_relationship(db, from_asset_id, to_asset_id, relationship_type, effective_date=effective_date)


def get_relationships(db: Session, asset_id: AssetId) -> Sequence[AssetRelationship]:
    return core.get_relationships(db, asset_id)


# ── Classification ───────────────────────────────────────────────────────────

def record_classification(
    db: Session,
    asset_id: AssetId,
    dimension: ClassificationDimension,
    value: str,
    source: str,
    *,
    as_of: Optional[datetime] = None,
) -> AssetClassification:
    return core.record_classification(db, asset_id, dimension, value, source, as_of=as_of)


def get_classifications(
    db: Session, asset_id: AssetId, *, dimension: Optional[ClassificationDimension] = None, current_only: bool = False,
) -> Sequence[AssetClassification]:
    return core.get_classifications(db, asset_id, dimension=dimension, current_only=current_only)


# ── Merge (explicit event, never silent cleanup) ────────────────────────────

def record_merge(
    db: Session,
    from_asset_id: AssetId,
    into_asset_id: AssetId,
    *,
    reason: str,
    recorded_by: Optional[str] = None,
) -> RegistryFinding:
    """Records that from_asset_id has merged into into_asset_id.

    Named record_merge (not merge_assets) deliberately: this operation's
    purpose is to durably record a merge decision that has already been
    made, not to perform identity mutation as its primary act. The status
    transition and relationship link are consequences of the recording, not
    the other way around. Composes two existing M1 primitives:
      - core.transition_status(from_asset_id, MERGED)
      - core.link_relationship(from_asset_id, into_asset_id, MERGED_INTO)
    and persists the merge as a RegistryFinding — created already RESOLVED,
    since recording a merge is itself the durable evidence of a decision,
    not something left open for adjudication. Returns that finding: the
    merge's permanent evidentiary record, not the mutated asset.
    """
    core.transition_status(db, from_asset_id, AssetStatus.MERGED)
    core.link_relationship(db, from_asset_id, into_asset_id, RelationshipType.MERGED_INTO)

    finding = findings_repo.create_finding(
        db,
        finding_type=FindingType.MERGE_RECORDED.value,
        subject_asset_id=from_asset_id,
        related_asset_id=into_asset_id,
        detail=f"asset_id={from_asset_id} merged into asset_id={into_asset_id}: {reason}",
    )
    return findings_repo.resolve_finding(
        db,
        finding,
        status=FindingStatus.RESOLVED.value,
        resolution=FindingResolution.MERGED.value,
        resolution_note=reason,
        resolved_by=recorded_by,
    )


# ── Findings adjudication (minimal surface) ─────────────────────────────────

def list_open_findings(db: Session, *, subject_asset_id: Optional[AssetId] = None) -> Sequence[RegistryFinding]:
    return findings_repo.list_findings(db, subject_asset_id=subject_asset_id, status=FindingStatus.OPEN.value)


def resolve_finding(
    db: Session,
    finding_id: int,
    *,
    resolution: FindingResolution,
    resolution_note: str,
    resolved_by: Optional[str] = None,
) -> RegistryFinding:
    """Closes out a finding. The original observation (what was found, when,
    about which assets) is never altered — only resolution fields are set,
    so the finding remains a permanent, appended-to record rather than
    being overwritten or removed."""
    finding = findings_repo.get_finding(db, finding_id)
    if finding is None:
        raise AssetRegistryError(f"no finding with id={finding_id}")

    status = FindingStatus.DISMISSED.value if resolution == FindingResolution.DISMISSED else FindingStatus.RESOLVED.value
    return findings_repo.resolve_finding(
        db,
        finding,
        status=status,
        resolution=resolution.value,
        resolution_note=resolution_note,
        resolved_by=resolved_by,
    )


# ── Bundled read ─────────────────────────────────────────────────────────────

def get_asset_detail(db: Session, asset_id: AssetId) -> Optional[AssetDetail]:
    asset = core.get_asset(db, asset_id)
    if asset is None:
        return None
    return AssetDetail(
        asset=asset,
        current_identifiers=core.get_identifiers(db, asset_id, current_only=True),
        current_classifications=core.get_classifications(db, asset_id, current_only=True),
        relationships=core.get_relationships(db, asset_id),
    )
