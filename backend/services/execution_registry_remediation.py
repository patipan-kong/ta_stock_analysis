"""Explicit-evidence M31.5 Registry remediation support.

Nothing in this module discovers an asset type from a symbol.  Every write
requires an approved manifest instruction with human-supplied evidence and
uses the existing Registry service boundary.  Dry-run is the default and is
implemented with a rolled-back savepoint.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from models.asset import Asset
from services import registry_lookup, registry_service
from services.asset_domain import (
    AssetClaim,
    AssetId,
    AssetType,
    ClassificationDimension,
    IdentifierRecord,
    IdentifierType,
    RelationshipType,
)

__all__ = [
    "RegistryRemediationOperation",
    "RegistryRemediationInstruction",
    "RegistryRemediationStep",
    "RegistryRemediationReport",
    "parse_registry_remediation_manifest",
    "apply_registry_remediation",
]


class RegistryRemediationOperation(str, Enum):
    MINT_ASSET = "MINT_ASSET"
    MINT_ETF = "MINT_ETF"
    MINT_DR = "MINT_DR"
    MINT_INDEX_REFERENCE = "MINT_INDEX_REFERENCE"
    ATTACH_IDENTIFIER = "ATTACH_IDENTIFIER"
    LINK_DR_RELATIONSHIP = "LINK_DR_RELATIONSHIP"
    REGISTER_INDEX_REFERENCE = "REGISTER_INDEX_REFERENCE"


_MINT_OPERATIONS = frozenset(
    {
        RegistryRemediationOperation.MINT_ASSET,
        RegistryRemediationOperation.MINT_ETF,
        RegistryRemediationOperation.MINT_DR,
        RegistryRemediationOperation.MINT_INDEX_REFERENCE,
    }
)


@dataclass(frozen=True)
class RegistryRemediationInstruction:
    instruction_id: str
    approved: bool
    operation: RegistryRemediationOperation
    evidence_source: str
    evidence_note: str
    requested_symbol: Optional[str] = None
    candidate_asset_ids: Tuple[int, ...] = ()
    asset_id: Optional[int] = None
    underlying_asset_id: Optional[int] = None
    canonical_symbol: Optional[str] = None
    display_symbol: Optional[str] = None
    asset_type: Optional[AssetType] = None
    market: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None
    tradable: Optional[bool] = None
    fractional_support: bool = False
    lot_size: Optional[int] = None
    settlement_cycle: Optional[str] = None
    identifiers: Tuple[IdentifierRecord, ...] = ()


@dataclass(frozen=True)
class RegistryRemediationStep:
    instruction_id: str
    operation: str
    status: str
    detail: str
    asset_id: Optional[int] = None


@dataclass(frozen=True)
class RegistryRemediationReport:
    dry_run: bool
    committed: bool
    steps: Tuple[RegistryRemediationStep, ...]

    def to_dict(self) -> dict:
        return {
            "dry_run": self.dry_run,
            "committed": self.committed,
            "steps": [step.__dict__ for step in self.steps],
        }


def _required_text(data: Mapping[str, object], key: str) -> str:
    value = str(data.get(key, "")).strip()
    if not value:
        raise ValueError(f"remediation manifest requires non-empty {key}")
    return value


def parse_registry_remediation_manifest(
    payload: Mapping[str, object],
) -> Tuple[RegistryRemediationInstruction, ...]:
    """Parse a versioned JSON-compatible manifest into typed instructions."""

    if payload.get("version") != 1:
        raise ValueError("remediation manifest version must be 1")
    raw_instructions = payload.get("instructions")
    if not isinstance(raw_instructions, list):
        raise ValueError("remediation manifest instructions must be a list")

    instructions = []
    seen_ids = set()
    for raw in raw_instructions:
        if not isinstance(raw, Mapping):
            raise ValueError("each remediation instruction must be an object")
        instruction_id = _required_text(raw, "instruction_id")
        if instruction_id in seen_ids:
            raise ValueError(f"duplicate remediation instruction_id={instruction_id!r}")
        seen_ids.add(instruction_id)
        operation = RegistryRemediationOperation(_required_text(raw, "operation"))

        identifier_records = []
        raw_identifiers = raw.get("identifiers", [])
        if not isinstance(raw_identifiers, list):
            raise ValueError(f"{instruction_id}: identifiers must be a list")
        raw_candidate_asset_ids = raw.get("candidate_asset_ids", [])
        if not isinstance(raw_candidate_asset_ids, list):
            raise ValueError(f"{instruction_id}: candidate_asset_ids must be a list")
        for identifier in raw_identifiers:
            if not isinstance(identifier, Mapping):
                raise ValueError(f"{instruction_id}: each identifier must be an object")
            identifier_records.append(
                IdentifierRecord(
                    identifier_type=IdentifierType(_required_text(identifier, "identifier_type")),
                    value=_required_text(identifier, "value"),
                    source=_required_text(identifier, "source"),
                )
            )

        raw_asset_type = raw.get("asset_type")
        instructions.append(
            RegistryRemediationInstruction(
                instruction_id=instruction_id,
                approved=raw.get("approved") is True,
                operation=operation,
                evidence_source=_required_text(raw, "evidence_source"),
                evidence_note=_required_text(raw, "evidence_note"),
                requested_symbol=(
                    str(raw["requested_symbol"]).strip()
                    if raw.get("requested_symbol")
                    else None
                ),
                candidate_asset_ids=tuple(
                    int(value) for value in raw_candidate_asset_ids
                ),
                asset_id=int(raw["asset_id"]) if raw.get("asset_id") is not None else None,
                underlying_asset_id=(
                    int(raw["underlying_asset_id"])
                    if raw.get("underlying_asset_id") is not None
                    else None
                ),
                canonical_symbol=(str(raw["canonical_symbol"]).strip() if raw.get("canonical_symbol") else None),
                display_symbol=(str(raw["display_symbol"]).strip() if raw.get("display_symbol") else None),
                asset_type=AssetType(str(raw_asset_type)) if raw_asset_type is not None else None,
                market=(str(raw["market"]).strip() if raw.get("market") else None),
                exchange=(str(raw["exchange"]).strip() if raw.get("exchange") else None),
                currency=(str(raw["currency"]).strip() if raw.get("currency") else None),
                tradable=raw.get("tradable") if isinstance(raw.get("tradable"), bool) else None,
                fractional_support=raw.get("fractional_support") is True,
                lot_size=int(raw["lot_size"]) if raw.get("lot_size") is not None else None,
                settlement_cycle=(str(raw["settlement_cycle"]).strip() if raw.get("settlement_cycle") else None),
                identifiers=tuple(identifier_records),
            )
        )
    return tuple(instructions)


def _validate_instruction(db: Session, instruction: RegistryRemediationInstruction) -> None:
    if not instruction.evidence_source or not instruction.evidence_note:
        raise ValueError(f"{instruction.instruction_id}: authoritative evidence is required")

    if instruction.operation in _MINT_OPERATIONS:
        missing = [
            name
            for name, value in (
                ("canonical_symbol", instruction.canonical_symbol),
                ("asset_type", instruction.asset_type),
                ("market", instruction.market),
                ("exchange", instruction.exchange),
                ("currency", instruction.currency),
                ("tradable", instruction.tradable),
            )
            if value is None or value == ""
        ]
        if missing:
            raise ValueError(
                f"{instruction.instruction_id}: {instruction.operation.value} requires "
                f"{', '.join(missing)}"
            )
        if not instruction.identifiers:
            raise ValueError(
                f"{instruction.instruction_id}: {instruction.operation.value} "
                "requires an explicit identifier"
            )
        if (
            instruction.operation == RegistryRemediationOperation.MINT_ETF
            and instruction.asset_type != AssetType.ETF
        ):
            raise ValueError(
                f"{instruction.instruction_id}: MINT_ETF requires explicit asset_type=ETF"
            )
        if instruction.operation == RegistryRemediationOperation.MINT_DR:
            if instruction.underlying_asset_id is None:
                raise ValueError(
                    f"{instruction.instruction_id}: MINT_DR requires authoritative underlying_asset_id"
                )
        elif instruction.underlying_asset_id is not None:
            raise ValueError(
                f"{instruction.instruction_id}: underlying_asset_id is accepted only by MINT_DR"
            )
        if instruction.operation == RegistryRemediationOperation.MINT_INDEX_REFERENCE and (
            instruction.asset_type != AssetType.OTHER or instruction.tradable is not False
        ):
            raise ValueError(
                f"{instruction.instruction_id}: MINT_INDEX_REFERENCE requires "
                "asset_type=OTHER and tradable=false"
            )
        if instruction.operation == RegistryRemediationOperation.MINT_DR:
            if registry_service.get_asset(db, AssetId(instruction.underlying_asset_id)) is None:
                raise ValueError(
                    f"{instruction.instruction_id}: authoritative underlying asset_id="
                    f"{instruction.underlying_asset_id} does not exist"
                )
        return

    if instruction.asset_id is None:
        raise ValueError(f"{instruction.instruction_id}: {instruction.operation.value} requires asset_id")
    asset = registry_service.get_asset(db, AssetId(instruction.asset_id))
    if asset is None:
        raise ValueError(f"{instruction.instruction_id}: asset_id={instruction.asset_id} does not exist")

    if instruction.operation == RegistryRemediationOperation.ATTACH_IDENTIFIER:
        if len(instruction.identifiers) != 1:
            raise ValueError(
                f"{instruction.instruction_id}: ATTACH_IDENTIFIER requires exactly one identifier"
            )
        if instruction.candidate_asset_ids != (instruction.asset_id,):
            raise ValueError(
                f"{instruction.instruction_id}: ATTACH_IDENTIFIER requires exactly one "
                "existing candidate matching asset_id"
            )
        if not instruction.requested_symbol:
            raise ValueError(
                f"{instruction.instruction_id}: ATTACH_IDENTIFIER requires requested_symbol"
            )
        from services.execution_registry_wave1 import exact_registry_candidates

        exact_candidate_ids = tuple(
            candidate.asset_id
            for candidate in exact_registry_candidates(db, instruction.requested_symbol)
        )
        if exact_candidate_ids != instruction.candidate_asset_ids:
            raise ValueError(
                f"{instruction.instruction_id}: candidate_asset_ids do not match the exact "
                f"Registry candidate set {exact_candidate_ids}"
            )
    elif instruction.operation == RegistryRemediationOperation.LINK_DR_RELATIONSHIP:
        if instruction.underlying_asset_id is None:
            raise ValueError(
                f"{instruction.instruction_id}: DR remediation requires authoritative underlying_asset_id"
            )
        if registry_service.get_asset(db, AssetId(instruction.underlying_asset_id)) is None:
            raise ValueError(
                f"{instruction.instruction_id}: underlying_asset_id="
                f"{instruction.underlying_asset_id} does not exist"
            )
        outgoing = [
            row
            for row in registry_service.get_relationships(db, AssetId(instruction.asset_id))
            if row.from_asset_id == instruction.asset_id
            and row.relationship_type == RelationshipType.DEPOSITARY_RECEIPT_OF.value
        ]
        if len(outgoing) > 1:
            raise ValueError(f"{instruction.instruction_id}: DR already has multiple outgoing relationships")
        if outgoing and outgoing[0].to_asset_id != instruction.underlying_asset_id:
            raise ValueError(
                f"{instruction.instruction_id}: DR already points to a different underlying asset"
            )
    elif instruction.operation == RegistryRemediationOperation.REGISTER_INDEX_REFERENCE:
        if asset.asset_type != AssetType.OTHER.value or asset.tradable is not False:
            raise ValueError(
                f"{instruction.instruction_id}: index reference requires existing "
                "AssetType.OTHER with tradable=false"
            )


def _apply_instruction(
    db: Session,
    instruction: RegistryRemediationInstruction,
) -> int:
    if instruction.operation in _MINT_OPERATIONS:
        asset = registry_service.mint_asset(
            db,
            AssetClaim(
                canonical_symbol=instruction.canonical_symbol or "",
                display_symbol=instruction.display_symbol,
                asset_type=instruction.asset_type or AssetType.OTHER,
                market=instruction.market or "",
                exchange=instruction.exchange or "",
                currency=instruction.currency or "",
                tradable=bool(instruction.tradable),
                fractional_support=instruction.fractional_support,
                lot_size=instruction.lot_size,
                settlement_cycle=instruction.settlement_cycle,
            ),
            identifiers=instruction.identifiers,
        )
        if instruction.operation == RegistryRemediationOperation.MINT_DR:
            registry_service.link_relationship(
                db,
                AssetId(asset.id),
                AssetId(instruction.underlying_asset_id),
                RelationshipType.DEPOSITARY_RECEIPT_OF,
            )
        elif instruction.operation == RegistryRemediationOperation.MINT_INDEX_REFERENCE:
            registry_service.record_classification(
                db,
                AssetId(asset.id),
                ClassificationDimension.ASSET_CLASS,
                "INDEX",
                instruction.evidence_source,
            )
        return int(asset.id)

    asset_id = AssetId(instruction.asset_id or 0)
    if instruction.operation == RegistryRemediationOperation.ATTACH_IDENTIFIER:
        registry_service.attach_identifier(db, asset_id, instruction.identifiers[0])
    elif instruction.operation == RegistryRemediationOperation.LINK_DR_RELATIONSHIP:
        registry_service.link_relationship(
            db,
            asset_id,
            AssetId(instruction.underlying_asset_id or 0),
            RelationshipType.DEPOSITARY_RECEIPT_OF,
        )
    elif instruction.operation == RegistryRemediationOperation.REGISTER_INDEX_REFERENCE:
        registry_service.record_classification(
            db,
            asset_id,
            ClassificationDimension.ASSET_CLASS,
            "INDEX",
            instruction.evidence_source,
        )
    return int(asset_id)


def _already_applied(
    db: Session,
    instruction: RegistryRemediationInstruction,
) -> Optional[int]:
    """Return the existing asset id only when the full instruction is current.

    This check makes a reviewed manifest safely repeatable.  A canonical-symbol
    collision with different metadata is deliberately an error, not an
    "already applied" shortcut.
    """

    if instruction.operation in _MINT_OPERATIONS:
        asset = (
            db.query(Asset)
            .filter(Asset.canonical_symbol == instruction.canonical_symbol)
            .one_or_none()
        )
        if asset is None:
            return None
        expected = {
            "asset_type": instruction.asset_type.value if instruction.asset_type else None,
            "market": instruction.market,
            "exchange": instruction.exchange,
            "currency": instruction.currency,
            "tradable": instruction.tradable,
            "fractional_support": instruction.fractional_support,
            "lot_size": instruction.lot_size,
            "settlement_cycle": instruction.settlement_cycle,
        }
        mismatches = [
            name for name, value in expected.items() if getattr(asset, name) != value
        ]
        if mismatches:
            raise ValueError(
                f"{instruction.instruction_id}: canonical_symbol="
                f"{instruction.canonical_symbol!r} already exists as asset_id={asset.id} "
                f"with conflicting {', '.join(mismatches)}"
            )
        current_identifiers = {
            (row.identifier_type, row.value)
            for row in registry_service.get_identifiers(
                db, AssetId(asset.id), current_only=True
            )
        }
        required_identifiers = {
            (identifier.identifier_type.value, identifier.value)
            for identifier in instruction.identifiers
        }
        if not required_identifiers.issubset(current_identifiers):
            raise ValueError(
                f"{instruction.instruction_id}: canonical asset_id={asset.id} exists but "
                "does not carry every requested current identifier"
            )
        if instruction.operation == RegistryRemediationOperation.MINT_DR:
            relationships = registry_service.get_relationships(db, AssetId(asset.id))
            if not any(
                row.from_asset_id == asset.id
                and row.to_asset_id == instruction.underlying_asset_id
                and row.relationship_type == RelationshipType.DEPOSITARY_RECEIPT_OF.value
                for row in relationships
            ):
                raise ValueError(
                    f"{instruction.instruction_id}: canonical DR asset exists without the "
                    "requested underlying relationship"
                )
        if instruction.operation == RegistryRemediationOperation.MINT_INDEX_REFERENCE:
            classifications = registry_service.get_classifications(
                db,
                AssetId(asset.id),
                dimension=ClassificationDimension.ASSET_CLASS,
                current_only=True,
            )
            if not any(
                row.value == "INDEX" and row.source == instruction.evidence_source
                for row in classifications
            ):
                raise ValueError(
                    f"{instruction.instruction_id}: canonical reference asset exists without "
                    "current ASSET_CLASS=INDEX"
                )
        return int(asset.id)

    asset_id = AssetId(instruction.asset_id or 0)
    if instruction.operation == RegistryRemediationOperation.ATTACH_IDENTIFIER:
        identifier = instruction.identifiers[0]
        current = registry_service.get_identifiers(db, asset_id, current_only=True)
        if any(
            row.identifier_type == identifier.identifier_type.value
            and row.value == identifier.value
            for row in current
        ):
            return int(asset_id)
    elif instruction.operation == RegistryRemediationOperation.LINK_DR_RELATIONSHIP:
        if any(
            row.from_asset_id == int(asset_id)
            and row.to_asset_id == instruction.underlying_asset_id
            and row.relationship_type == RelationshipType.DEPOSITARY_RECEIPT_OF.value
            for row in registry_service.get_relationships(db, asset_id)
        ):
            return int(asset_id)
    elif instruction.operation == RegistryRemediationOperation.REGISTER_INDEX_REFERENCE:
        if any(
            row.value == "INDEX"
            for row in registry_service.get_classifications(
                db,
                asset_id,
                dimension=ClassificationDimension.ASSET_CLASS,
                current_only=True,
            )
        ):
            return int(asset_id)
    return None


def apply_registry_remediation(
    db: Session,
    instructions: Sequence[RegistryRemediationInstruction],
    *,
    commit: bool = False,
) -> RegistryRemediationReport:
    """Validate and apply only approved instructions; dry-run by default."""

    approved = [instruction for instruction in instructions if instruction.approved]
    steps = [
        RegistryRemediationStep(
            instruction_id=instruction.instruction_id,
            operation=instruction.operation.value,
            status="SKIPPED_NOT_APPROVED",
            detail="manifest instruction is not explicitly approved",
        )
        for instruction in instructions
        if not instruction.approved
    ]

    for instruction in approved:
        _validate_instruction(db, instruction)

    savepoint = None if commit else db.begin_nested()
    try:
        for instruction in approved:
            existing_asset_id = _already_applied(db, instruction)
            if existing_asset_id is None:
                asset_id = _apply_instruction(db, instruction)
                db.flush()
                status = "APPLIED" if commit else "WOULD_APPLY"
            else:
                asset_id = existing_asset_id
                status = "ALREADY_APPLIED"
            steps.append(
                RegistryRemediationStep(
                    instruction_id=instruction.instruction_id,
                    operation=instruction.operation.value,
                    status=status,
                    detail=(
                        f"approved evidence source={instruction.evidence_source}; "
                        f"note={instruction.evidence_note}"
                    ),
                    asset_id=asset_id,
                )
            )
        if commit:
            db.commit()
        elif savepoint is not None and savepoint.is_active:
            savepoint.rollback()
    except Exception:
        if savepoint is not None and savepoint.is_active:
            savepoint.rollback()
        else:
            db.rollback()
        raise
    finally:
        registry_lookup.invalidate_cache()

    return RegistryRemediationReport(
        dry_run=not commit,
        committed=commit,
        steps=tuple(steps),
    )
