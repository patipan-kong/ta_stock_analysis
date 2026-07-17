"""M32.3E3R2 read-only Registry lot-capability evidence preflight.

This module deliberately has no update function.  It can parse and assess
human-supplied evidence, but it cannot project that evidence into ``Asset``
or create an evidence row.  The separation keeps R2 incapable of making a
lot-size or fractional-trading decision authoritative.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from models.asset import Asset, AssetIdentifier
from models.database import PortfolioItem, Transaction
from services.asset_definitions import (
    BindingResolver,
    DefinitionRegistry,
    DefinitionRegistryError,
    UnresolvedBindingError,
)

__all__ = [
    "LotCapabilityUnit",
    "LotCapabilityScope",
    "LotCapabilitySemantics",
    "LotCapabilitySourceType",
    "LotCapabilityConfidence",
    "LotCapabilityApprovalState",
    "LotCapabilityPreflightOutcome",
    "RegistryIdentitySnapshot",
    "LotCapabilityEvidence",
    "ExpectedLotCapabilityProjection",
    "LotCapabilityRollbackSnapshot",
    "LotCapabilityManifestInstruction",
    "LotCapabilityManifest",
    "ApprovedLotCapabilityAuthority",
    "LotCapabilityAuthorityTrust",
    "LotCapabilityManifestError",
    "LotCapabilityAssetReport",
    "LotCapabilityPreflightReport",
    "build_lot_capability_evidence",
    "parse_lot_capability_manifest",
    "build_lot_capability_preflight",
]


_CONTRACT_VERSION = "1"
_REPORT_VERSION = "m32.3e3r2-v1"
_EXECUTABLE_TRANSACTION_TYPES = ("BUY", "SELL", "INITIAL_POSITION")


class LotCapabilityUnit(str, Enum):
    SHARE = "SHARE"


class LotCapabilityScope(str, Enum):
    STANDARD_BOARD_EXECUTION = "STANDARD_BOARD_EXECUTION"


class LotCapabilitySemantics(str, Enum):
    QUANTITY_INCREMENT = "QUANTITY_INCREMENT"


class LotCapabilitySourceType(str, Enum):
    EXCHANGE_MASTER = "EXCHANGE_MASTER"
    LISTING_NOTICE = "LISTING_NOTICE"
    OFFICIAL_INSTRUMENT_MASTER = "OFFICIAL_INSTRUMENT_MASTER"


class LotCapabilityConfidence(str, Enum):
    VERIFIED = "VERIFIED"
    CONFLICTED = "CONFLICTED"
    INSUFFICIENT = "INSUFFICIENT"


class LotCapabilityApprovalState(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"


class LotCapabilityPreflightOutcome(str, Enum):
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    UNVERIFIED_DEFAULT = "UNVERIFIED_DEFAULT"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    CONFLICT = "CONFLICT"
    STALE_SOURCE = "STALE_SOURCE"
    FUTURE_EFFECTIVE = "FUTURE_EFFECTIVE"
    EXPIRED_EVIDENCE = "EXPIRED_EVIDENCE"
    INVALID_VALUE = "INVALID_VALUE"
    DEFINITION_REFINEMENT_NOT_PERMITTED = "DEFINITION_REFINEMENT_NOT_PERMITTED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    QUARANTINED = "QUARANTINED"


class LotCapabilityManifestError(ValueError):
    """A supplied evidence manifest is not a valid R2 review artifact."""


def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LotCapabilityManifestError(f"{name} must be a non-empty string")
    return value.strip()


def _require_bounded_text(value: object, name: str, maximum: int) -> str:
    rendered = _require_text(value, name)
    if len(rendered) > maximum:
        raise LotCapabilityManifestError(f"{name} must be no longer than {maximum} characters")
    return rendered


def _require_aware(value: object, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise LotCapabilityManifestError(f"{name} must be a timezone-aware datetime")
    return value


def _require_positive_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise LotCapabilityManifestError(f"{name} must be an explicit positive integer")
    return value


def _require_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise LotCapabilityManifestError(f"{name} must be an explicit boolean")
    return value


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    return value


@dataclass(frozen=True)
class RegistryIdentitySnapshot:
    """Explicit identity evidence; this object never generates aliases."""

    canonical_symbol: str
    current_identifiers: Tuple[Tuple[str, str], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "canonical_symbol", _require_text(self.canonical_symbol, "canonical_symbol"))
        if not self.current_identifiers or len(self.current_identifiers) > 32:
            raise LotCapabilityManifestError("current_identifiers must contain 1 to 32 explicit entries")
        normalized = []
        for item in self.current_identifiers:
            if not isinstance(item, tuple) or len(item) != 2:
                raise LotCapabilityManifestError("each current identifier must be a (type, value) tuple")
            normalized.append((_require_text(item[0], "identifier_type"), _require_text(item[1], "identifier_value")))
        normalized_tuple = tuple(sorted(set(normalized)))
        if len(normalized_tuple) != len(normalized):
            raise LotCapabilityManifestError("current_identifiers must not contain duplicates")
        object.__setattr__(self, "current_identifiers", normalized_tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "canonical_symbol": self.canonical_symbol,
            "current_identifiers": [
                {"identifier_type": identifier_type, "value": value}
                for identifier_type, value in self.current_identifiers
            ],
        }


@dataclass(frozen=True)
class LotCapabilityEvidence:
    """Versioned, immutable, externally supplied capability evidence.

    ``evidence_ref`` is derived from all normalized fields other than itself.
    A caller may supply the expected reference, but cannot select a different
    one; this lets manifests be independently reviewed while remaining
    deterministic.
    """

    contract_version: str
    asset_id: int
    registry_identity_snapshot: RegistryIdentitySnapshot
    unit: LotCapabilityUnit
    scope: LotCapabilityScope
    lot_semantics: LotCapabilitySemantics
    lot_size: int
    fractional_support: bool
    source_id: str
    source_type: LotCapabilitySourceType
    source_locator: str
    source_record_key: str
    source_version: str
    source_published_at: datetime
    source_retrieved_at: datetime
    authority: str
    confidence: LotCapabilityConfidence
    effective_from: datetime
    effective_to: Optional[datetime]
    provenance: Tuple[str, ...]
    reviewed_by: str
    reviewed_at: datetime
    approval_state: LotCapabilityApprovalState
    approval_note: str
    supersedes_evidence_ref: Optional[str] = None
    rollback_of_evidence_ref: Optional[str] = None
    evidence_ref: str = ""

    def __post_init__(self) -> None:
        _require_text(self.contract_version, "contract_version")
        _require_positive_int(self.asset_id, "asset_id")
        _require_positive_int(self.lot_size, "lot_size")
        _require_bool(self.fractional_support, "fractional_support")
        for name, maximum in (
            ("source_id", 128), ("source_locator", 1024), ("source_record_key", 512),
            ("source_version", 128), ("authority", 256), ("reviewed_by", 256), ("approval_note", 1024),
        ):
            _require_bounded_text(getattr(self, name), name, maximum)
        for name in ("source_published_at", "source_retrieved_at", "effective_from", "reviewed_at"):
            _require_aware(getattr(self, name), name)
        if self.effective_to is not None:
            _require_aware(self.effective_to, "effective_to")
            if self.effective_to <= self.effective_from:
                raise LotCapabilityManifestError("effective_to must be later than effective_from")
        if not isinstance(self.unit, LotCapabilityUnit):
            raise LotCapabilityManifestError("unit must be a governed LotCapabilityUnit")
        if not isinstance(self.scope, LotCapabilityScope):
            raise LotCapabilityManifestError("scope must be a governed LotCapabilityScope")
        if not isinstance(self.lot_semantics, LotCapabilitySemantics):
            raise LotCapabilityManifestError("lot_semantics must be a governed LotCapabilitySemantics")
        if not isinstance(self.source_type, LotCapabilitySourceType):
            raise LotCapabilityManifestError("source_type must be a governed official source type")
        if not isinstance(self.confidence, LotCapabilityConfidence):
            raise LotCapabilityManifestError("confidence must be a governed LotCapabilityConfidence")
        if not isinstance(self.approval_state, LotCapabilityApprovalState):
            raise LotCapabilityManifestError("approval_state must be a governed LotCapabilityApprovalState")
        if self.approval_state == LotCapabilityApprovalState.APPROVED and self.confidence != LotCapabilityConfidence.VERIFIED:
            raise LotCapabilityManifestError("APPROVED evidence must also be VERIFIED")
        if not isinstance(self.provenance, tuple) or not self.provenance or len(self.provenance) > 16:
            raise LotCapabilityManifestError("provenance must contain 1 to 16 bounded entries")
        if any(not isinstance(item, str) or not item.strip() or len(item) > 512 for item in self.provenance):
            raise LotCapabilityManifestError("provenance entries must be non-empty strings no longer than 512 characters")
        for name in ("supersedes_evidence_ref", "rollback_of_evidence_ref"):
            value = getattr(self, name)
            if value is not None:
                _require_text(value, name)
        expected = self.computed_evidence_ref()
        if self.evidence_ref and self.evidence_ref != expected:
            raise LotCapabilityManifestError("evidence_ref does not match normalized immutable content")
        object.__setattr__(self, "evidence_ref", expected)

    def _reference_payload(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "asset_id": self.asset_id,
            "registry_identity_snapshot": self.registry_identity_snapshot.to_dict(),
            "unit": self.unit.value,
            "scope": self.scope.value,
            "lot_semantics": self.lot_semantics.value,
            "lot_size": self.lot_size,
            "fractional_support": self.fractional_support,
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "source_locator": self.source_locator,
            "source_record_key": self.source_record_key,
            "source_version": self.source_version,
            "source_published_at": self.source_published_at.isoformat(),
            "source_retrieved_at": self.source_retrieved_at.isoformat(),
            "authority": self.authority,
            "confidence": self.confidence.value,
            "effective_from": self.effective_from.isoformat(),
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "provenance": list(self.provenance),
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat(),
            "approval_state": self.approval_state.value,
            "approval_note": self.approval_note,
            "supersedes_evidence_ref": self.supersedes_evidence_ref,
            "rollback_of_evidence_ref": self.rollback_of_evidence_ref,
        }

    def computed_evidence_ref(self) -> str:
        payload = json.dumps(self._reference_payload(), sort_keys=True, separators=(",", ":"))
        return "lce_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]

    def to_dict(self) -> dict[str, object]:
        payload = self._reference_payload()
        payload["evidence_ref"] = self.evidence_ref
        return payload


def build_lot_capability_evidence(**kwargs: object) -> LotCapabilityEvidence:
    """Build an evidence object and derive its deterministic reference."""

    return LotCapabilityEvidence(**kwargs)  # type: ignore[arg-type]


@dataclass(frozen=True)
class ExpectedLotCapabilityProjection:
    canonical_symbol: str
    lot_size: Optional[int]
    fractional_support: bool
    asset_updated_at: datetime

    def __post_init__(self) -> None:
        _require_text(self.canonical_symbol, "expected_current.canonical_symbol")
        if self.lot_size is not None:
            _require_positive_int(self.lot_size, "expected_current.lot_size")
        _require_bool(self.fractional_support, "expected_current.fractional_support")
        _require_aware(self.asset_updated_at, "expected_current.asset_updated_at")


@dataclass(frozen=True)
class LotCapabilityRollbackSnapshot:
    prior_lot_size: Optional[int]
    prior_fractional_support: bool
    implication: str

    def __post_init__(self) -> None:
        if self.prior_lot_size is not None:
            _require_positive_int(self.prior_lot_size, "rollback.prior_lot_size")
        _require_bool(self.prior_fractional_support, "rollback.prior_fractional_support")
        _require_text(self.implication, "rollback.implication")


@dataclass(frozen=True)
class LotCapabilityManifestInstruction:
    instruction_id: str
    asset_id: int
    expected_current: ExpectedLotCapabilityProjection
    evidence: LotCapabilityEvidence
    rollback: LotCapabilityRollbackSnapshot
    operation: str = "UPDATE_LOT_CAPABILITY"

    def __post_init__(self) -> None:
        _require_text(self.instruction_id, "instruction_id")
        _require_positive_int(self.asset_id, "asset_id")
        if self.operation != "UPDATE_LOT_CAPABILITY":
            raise LotCapabilityManifestError("operation must be UPDATE_LOT_CAPABILITY")
        if self.evidence.asset_id != self.asset_id:
            raise LotCapabilityManifestError("evidence.asset_id must equal instruction asset_id")


@dataclass(frozen=True)
class LotCapabilityManifest:
    manifest_version: int
    manifest_id: str
    instructions: Tuple[LotCapabilityManifestInstruction, ...]

    def __post_init__(self) -> None:
        if self.manifest_version != 1:
            raise LotCapabilityManifestError("manifest_version must be 1")
        _require_text(self.manifest_id, "manifest_id")
        if not isinstance(self.instructions, tuple):
            raise LotCapabilityManifestError("instructions must be an immutable tuple")
        instruction_ids = [item.instruction_id for item in self.instructions]
        if len(instruction_ids) != len(set(instruction_ids)):
            raise LotCapabilityManifestError("duplicate instruction_id")
        evidence_refs = [item.evidence.evidence_ref for item in self.instructions]
        if len(evidence_refs) != len(set(evidence_refs)):
            raise LotCapabilityManifestError("duplicate evidence_ref")
        by_asset: dict[int, list[LotCapabilityManifestInstruction]] = defaultdict(list)
        for item in self.instructions:
            by_asset[item.asset_id].append(item)
        for asset_id, asset_instructions in by_asset.items():
            if len(asset_instructions) > 1:
                if _has_effective_overlap([item.evidence for item in asset_instructions]):
                    raise LotCapabilityManifestError(f"overlapping effective periods for asset_id={asset_id}")
                raise LotCapabilityManifestError(f"multiple instructions for asset_id={asset_id}")
        refs = set(evidence_refs)
        for item in self.instructions:
            supersedes = item.evidence.supersedes_evidence_ref
            if supersedes is not None and supersedes not in refs:
                raise LotCapabilityManifestError("supersession reference does not resolve inside supplied evidence")
            rollback_of = item.evidence.rollback_of_evidence_ref
            if rollback_of is not None and rollback_of not in refs:
                raise LotCapabilityManifestError("rollback reference does not resolve inside supplied evidence")


def _has_effective_overlap(evidence: Sequence[LotCapabilityEvidence]) -> bool:
    ordered = sorted(evidence, key=lambda item: item.effective_from)
    for previous, current in zip(ordered, ordered[1:]):
        if previous.effective_to is None or current.effective_from < previous.effective_to:
            return True
    return False


@dataclass(frozen=True)
class ApprovedLotCapabilityAuthority:
    source_id: str
    authority: str
    source_types: Tuple[LotCapabilitySourceType, ...]

    def __post_init__(self) -> None:
        _require_text(self.source_id, "authority.source_id")
        _require_text(self.authority, "authority.authority")
        if not self.source_types or any(not isinstance(item, LotCapabilitySourceType) for item in self.source_types):
            raise LotCapabilityManifestError("authority.source_types must contain governed source types")


@dataclass(frozen=True)
class LotCapabilityAuthorityTrust:
    """Explicitly injected trust configuration; no environment read occurs."""

    entries: Tuple[ApprovedLotCapabilityAuthority, ...] = ()

    def __post_init__(self) -> None:
        ids = [entry.source_id for entry in self.entries]
        if len(ids) != len(set(ids)):
            raise LotCapabilityManifestError("authority trust contains duplicate source_id")

    def accepts(self, evidence: LotCapabilityEvidence) -> bool:
        return any(
            entry.source_id == evidence.source_id
            and entry.authority == evidence.authority
            and evidence.source_type in entry.source_types
            for entry in self.entries
        )


@dataclass(frozen=True)
class LotCapabilityCandidateEvidence:
    label: str
    holding_quantities: Tuple[str, ...]
    transaction_quantities: Tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "holding_quantities": list(self.holding_quantities),
            "transaction_quantities": list(self.transaction_quantities),
        }


@dataclass(frozen=True)
class LotCapabilityAssetReport:
    asset_id: int
    canonical_symbol: str
    identifiers: Tuple[Tuple[str, str, str], ...]
    asset_type: str
    market: str
    exchange: str
    currency: str
    current_lot_size: Optional[int]
    current_fractional_support: bool
    governed_evidence_present: bool
    lot_refinement_permitted: Optional[bool]
    fractional_refinement_permitted: Optional[bool]
    definition_consultation_error: Optional[str]
    supplied_evidence_refs: Tuple[str, ...]
    supplied_evidence_decisions: Tuple[Mapping[str, object], ...]
    identity_match: Optional[bool]
    effective_period_result: Optional[str]
    conflict: bool
    candidate_operational_evidence: LotCapabilityCandidateEvidence
    outcome: LotCapabilityPreflightOutcome
    missing_requirements: Tuple[str, ...]
    details: Tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "asset_id": self.asset_id,
            "canonical_symbol": self.canonical_symbol,
            "identifiers": [
                {"identifier_type": item[0], "value": item[1], "source": item[2]}
                for item in self.identifiers
            ],
            "asset_type": self.asset_type,
            "market": self.market,
            "exchange": self.exchange,
            "currency": self.currency,
            "current_lot_size": self.current_lot_size,
            "current_fractional_support": self.current_fractional_support,
            "governed_evidence_present": self.governed_evidence_present,
            "asset_definition": {
                "lot_refinement_permitted": self.lot_refinement_permitted,
                "fractional_refinement_permitted": self.fractional_refinement_permitted,
                "consultation_error": self.definition_consultation_error,
            },
            "supplied_evidence_refs": list(self.supplied_evidence_refs),
            "supplied_evidence_decisions": [dict(item) for item in self.supplied_evidence_decisions],
            "identity_match": self.identity_match,
            "effective_period_result": self.effective_period_result,
            "conflict": self.conflict,
            "candidate_operational_evidence": self.candidate_operational_evidence.to_dict(),
            "outcome": self.outcome.value,
            "missing_requirements": list(self.missing_requirements),
            "details": list(self.details),
        }


@dataclass(frozen=True)
class LotCapabilityPreflightReport:
    report_version: str
    generated_at: datetime
    environment_reference: str
    source_references: Tuple[str, ...]
    registry_population_count: int
    raw_capability_coverage: Mapping[str, int]
    governed_evidence_coverage: Mapping[str, int]
    outcome_counts: Mapping[str, int]
    assets: Tuple[LotCapabilityAssetReport, ...]
    manifest_validation: Mapping[str, object]
    no_writes_performed: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "report_version": self.report_version,
            "generated_at": self.generated_at.isoformat(),
            "environment_reference": self.environment_reference,
            "source_references": list(self.source_references),
            "registry_population_count": self.registry_population_count,
            "raw_capability_coverage": dict(sorted(self.raw_capability_coverage.items())),
            "governed_evidence_coverage": dict(sorted(self.governed_evidence_coverage.items())),
            "outcome_counts": dict(sorted(self.outcome_counts.items())),
            "assets": [item.to_dict() for item in self.assets],
            "manifest_validation": _json_value(self.manifest_validation),
            "no_writes_performed": True,
            "commit_capability": "UNSUPPORTED_IN_M32_3E3R2",
        }


def _parse_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise LotCapabilityManifestError(f"{field_name} must be an ISO-8601 timestamp string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LotCapabilityManifestError(f"{field_name} must be an ISO-8601 timestamp") from exc
    return _require_aware(parsed, field_name)


def _parse_enum(enum_type, value: object, field_name: str):
    if not isinstance(value, str):
        raise LotCapabilityManifestError(f"{field_name} must be an explicit string enum value")
    try:
        return enum_type(value)
    except ValueError as exc:
        raise LotCapabilityManifestError(f"{field_name} is not a governed value") from exc


def _parse_identity(raw: object) -> RegistryIdentitySnapshot:
    if not isinstance(raw, Mapping):
        raise LotCapabilityManifestError("registry_identity_snapshot must be an object")
    identifiers = raw.get("current_identifiers")
    if not isinstance(identifiers, list):
        raise LotCapabilityManifestError("registry_identity_snapshot.current_identifiers must be a list")
    pairs = []
    for item in identifiers:
        if not isinstance(item, Mapping):
            raise LotCapabilityManifestError("current identifier must be an object")
        pairs.append((_require_text(item.get("identifier_type"), "identifier_type"), _require_text(item.get("value"), "identifier value")))
    return RegistryIdentitySnapshot(_require_text(raw.get("canonical_symbol"), "canonical_symbol"), tuple(pairs))


def _parse_evidence(raw: object) -> LotCapabilityEvidence:
    if not isinstance(raw, Mapping):
        raise LotCapabilityManifestError("evidence must be an object")
    required = (
        "contract_version", "evidence_ref", "asset_id", "registry_identity_snapshot", "unit", "scope",
        "lot_semantics", "lot_size", "fractional_support", "source_id", "source_type", "source_locator",
        "source_record_key", "source_version", "source_published_at", "source_retrieved_at", "authority",
        "confidence", "effective_from", "effective_to", "provenance", "reviewed_by", "reviewed_at", "approval_state", "approval_note",
        "supersedes_evidence_ref", "rollback_of_evidence_ref",
    )
    missing = [key for key in required if key not in raw]
    if missing:
        raise LotCapabilityManifestError("evidence missing required fields: " + ", ".join(missing))
    provenance = raw.get("provenance")
    if not isinstance(provenance, list):
        raise LotCapabilityManifestError("provenance must be an explicit list")
    return LotCapabilityEvidence(
        contract_version=_require_text(raw.get("contract_version"), "contract_version"),
        evidence_ref=_require_text(raw.get("evidence_ref"), "evidence_ref"),
        asset_id=_require_positive_int(raw.get("asset_id"), "evidence.asset_id"),
        registry_identity_snapshot=_parse_identity(raw.get("registry_identity_snapshot")),
        unit=_parse_enum(LotCapabilityUnit, raw.get("unit"), "unit"),
        scope=_parse_enum(LotCapabilityScope, raw.get("scope"), "scope"),
        lot_semantics=_parse_enum(LotCapabilitySemantics, raw.get("lot_semantics"), "lot_semantics"),
        lot_size=_require_positive_int(raw.get("lot_size"), "lot_size"),
        fractional_support=_require_bool(raw.get("fractional_support"), "fractional_support"),
        source_id=_require_text(raw.get("source_id"), "source_id"),
        source_type=_parse_enum(LotCapabilitySourceType, raw.get("source_type"), "source_type"),
        source_locator=_require_text(raw.get("source_locator"), "source_locator"),
        source_record_key=_require_text(raw.get("source_record_key"), "source_record_key"),
        source_version=_require_text(raw.get("source_version"), "source_version"),
        source_published_at=_parse_datetime(raw.get("source_published_at"), "source_published_at"),
        source_retrieved_at=_parse_datetime(raw.get("source_retrieved_at"), "source_retrieved_at"),
        authority=_require_text(raw.get("authority"), "authority"),
        confidence=_parse_enum(LotCapabilityConfidence, raw.get("confidence"), "confidence"),
        effective_from=_parse_datetime(raw.get("effective_from"), "effective_from"),
        effective_to=(_parse_datetime(raw["effective_to"], "effective_to") if raw.get("effective_to") is not None else None),
        provenance=tuple(raw["provenance"]),
        reviewed_by=_require_text(raw.get("reviewed_by"), "reviewed_by"),
        reviewed_at=_parse_datetime(raw.get("reviewed_at"), "reviewed_at"),
        approval_state=_parse_enum(LotCapabilityApprovalState, raw.get("approval_state"), "approval_state"),
        approval_note=_require_text(raw.get("approval_note"), "approval_note"),
        supersedes_evidence_ref=(str(raw["supersedes_evidence_ref"]).strip() if raw.get("supersedes_evidence_ref") is not None else None),
        rollback_of_evidence_ref=(str(raw["rollback_of_evidence_ref"]).strip() if raw.get("rollback_of_evidence_ref") is not None else None),
    )


def parse_lot_capability_manifest(raw: Mapping[str, object]) -> LotCapabilityManifest:
    """Strictly parse a review-only manifest.  It has no commit mode."""

    if not isinstance(raw, Mapping):
        raise LotCapabilityManifestError("manifest must be an object")
    version = raw.get("manifest_version", raw.get("version"))
    if not isinstance(version, int) or isinstance(version, bool):
        raise LotCapabilityManifestError("manifest_version must be integer 1")
    instructions_raw = raw.get("instructions")
    if not isinstance(instructions_raw, list):
        raise LotCapabilityManifestError("instructions must be a list")
    instructions = []
    for item in instructions_raw:
        if not isinstance(item, Mapping):
            raise LotCapabilityManifestError("instruction must be an object")
        for name in ("instruction_id", "operation", "asset_id", "expected_current", "proposed", "evidence", "rollback"):
            if name not in item:
                raise LotCapabilityManifestError(f"instruction missing required field {name}")
        expected = item["expected_current"]
        proposed = item["proposed"]
        rollback = item["rollback"]
        if not isinstance(expected, Mapping) or not isinstance(proposed, Mapping) or not isinstance(rollback, Mapping):
            raise LotCapabilityManifestError("expected_current, proposed, and rollback must be objects")
        evidence = _parse_evidence(item["evidence"])
        for name in ("unit", "scope", "lot_semantics", "lot_size", "fractional_support", "effective_from"):
            if name not in proposed:
                raise LotCapabilityManifestError(f"proposed missing required field {name}")
        proposed_lot = _require_positive_int(proposed.get("lot_size"), "proposed.lot_size")
        proposed_fractional = _require_bool(proposed.get("fractional_support"), "proposed.fractional_support")
        if proposed_lot != evidence.lot_size or proposed_fractional != evidence.fractional_support:
            raise LotCapabilityManifestError("proposed capability values must exactly match evidence")
        if _parse_enum(LotCapabilityUnit, proposed.get("unit"), "proposed.unit") != evidence.unit:
            raise LotCapabilityManifestError("proposed.unit must exactly match evidence")
        if _parse_enum(LotCapabilityScope, proposed.get("scope"), "proposed.scope") != evidence.scope:
            raise LotCapabilityManifestError("proposed.scope must exactly match evidence")
        if _parse_enum(LotCapabilitySemantics, proposed.get("lot_semantics"), "proposed.lot_semantics") != evidence.lot_semantics:
            raise LotCapabilityManifestError("proposed.lot_semantics must exactly match evidence")
        if _parse_datetime(proposed.get("effective_from"), "proposed.effective_from") != evidence.effective_from:
            raise LotCapabilityManifestError("proposed.effective_from must exactly match evidence")
        instructions.append(LotCapabilityManifestInstruction(
            instruction_id=_require_text(item.get("instruction_id"), "instruction_id"),
            operation=_require_text(item.get("operation"), "operation"),
            asset_id=_require_positive_int(item.get("asset_id"), "asset_id"),
            expected_current=ExpectedLotCapabilityProjection(
                canonical_symbol=_require_text(expected.get("canonical_symbol"), "expected_current.canonical_symbol"),
                lot_size=(None if expected.get("lot_size") is None else _require_positive_int(expected.get("lot_size"), "expected_current.lot_size")),
                fractional_support=_require_bool(expected.get("fractional_support"), "expected_current.fractional_support"),
                asset_updated_at=_parse_datetime(expected.get("asset_updated_at"), "expected_current.asset_updated_at"),
            ),
            evidence=evidence,
            rollback=LotCapabilityRollbackSnapshot(
                prior_lot_size=(None if rollback.get("prior_lot_size") is None else _require_positive_int(rollback.get("prior_lot_size"), "rollback.prior_lot_size")),
                prior_fractional_support=_require_bool(rollback.get("prior_fractional_support"), "rollback.prior_fractional_support"),
                implication=_require_text(rollback.get("implication"), "rollback.implication"),
            ),
        ))
    return LotCapabilityManifest(
        manifest_version=version,
        manifest_id=_require_text(raw.get("manifest_id"), "manifest_id"),
        instructions=tuple(instructions),
    )


def _definition_permissions(asset_type: str, resolver: Optional[BindingResolver], boot_error: Optional[str]) -> tuple[Optional[bool], Optional[bool], Optional[str]]:
    if boot_error is not None or resolver is None:
        return None, None, boot_error or "Asset Definition resolver unavailable"
    try:
        view = resolver.resolve(asset_type)
        return view.unit_permits_lot_refinement(), view.unit_permits_fractional_refinement(), None
    except (UnresolvedBindingError, ValueError) as exc:
        return None, None, f"{type(exc).__name__}: {exc}"


def _current_identifiers_by_asset(db: Session, asset_ids: Sequence[int]) -> dict[int, tuple[tuple[str, str, str], ...]]:
    result: dict[int, list[tuple[str, str, str]]] = defaultdict(list)
    if asset_ids:
        rows = db.query(AssetIdentifier).filter(
            AssetIdentifier.asset_id.in_(asset_ids), AssetIdentifier.is_current.is_(True)
        ).order_by(AssetIdentifier.asset_id, AssetIdentifier.identifier_type, AssetIdentifier.value).all()
        for row in rows:
            result[int(row.asset_id)].append((str(row.identifier_type), str(row.value), str(row.source)))
    return {asset_id: tuple(values) for asset_id, values in result.items()}


def _candidate_evidence(db: Session, identifiers_by_asset: Mapping[int, tuple[tuple[str, str, str], ...]]) -> dict[int, LotCapabilityCandidateEvidence]:
    lookup: dict[str, list[int]] = defaultdict(list)
    for asset_id, identifiers in identifiers_by_asset.items():
        for _kind, value, _source in identifiers:
            lookup[value].append(asset_id)
    holdings: dict[int, list[str]] = defaultdict(list)
    transactions: dict[int, list[str]] = defaultdict(list)
    for row in db.query(PortfolioItem.symbol, PortfolioItem.shares).all():
        for asset_id in lookup.get(str(row.symbol), ()):
            holdings[asset_id].append(_quantity_text(row.shares))
    for row in db.query(Transaction.symbol, Transaction.shares).filter(
        Transaction.transaction_type.in_(_EXECUTABLE_TRANSACTION_TYPES)
    ).all():
        if row.shares is None:
            continue
        for asset_id in lookup.get(str(row.symbol), ()):
            transactions[asset_id].append(_quantity_text(row.shares))
    return {
        asset_id: LotCapabilityCandidateEvidence(
            label="NON_AUTHORITATIVE_CANDIDATE_EVIDENCE",
            holding_quantities=tuple(sorted(holdings.get(asset_id, ()), key=lambda value: (len(value), value))),
            transaction_quantities=tuple(sorted(set(transactions.get(asset_id, ())), key=lambda value: (len(value), value))),
        )
        for asset_id in identifiers_by_asset
    }


def _quantity_text(value: object) -> str:
    return format(float(value), ".12g")


def _matches_identity(asset: Asset, identifiers: tuple[tuple[str, str, str], ...], evidence: LotCapabilityEvidence) -> bool:
    actual = tuple(sorted((kind, value) for kind, value, _source in identifiers))
    return asset.canonical_symbol == evidence.registry_identity_snapshot.canonical_symbol and actual == evidence.registry_identity_snapshot.current_identifiers


def _effective_outcome(evidence: LotCapabilityEvidence, generated_at: datetime) -> Optional[LotCapabilityPreflightOutcome]:
    if evidence.effective_from > generated_at:
        return LotCapabilityPreflightOutcome.FUTURE_EFFECTIVE
    if evidence.effective_to is not None and evidence.effective_to <= generated_at:
        return LotCapabilityPreflightOutcome.EXPIRED_EVIDENCE
    return None


def _manifest_validation(manifest: Optional[LotCapabilityManifest], assets: Mapping[int, Asset]) -> Mapping[str, object]:
    if manifest is None:
        return MappingProxyType({"supplied": False, "valid": True, "instructions": []})
    decisions = []
    for instruction in manifest.instructions:
        asset = assets.get(instruction.asset_id)
        if asset is None:
            decisions.append({"instruction_id": instruction.instruction_id, "status": "UNKNOWN_ASSET"})
            continue
        expected = instruction.expected_current
        matches = (
            asset.canonical_symbol == expected.canonical_symbol
            and asset.lot_size == expected.lot_size
            and asset.fractional_support == expected.fractional_support
            and _as_aware(asset.updated_at) == expected.asset_updated_at
        )
        decisions.append({
            "instruction_id": instruction.instruction_id,
            "asset_id": instruction.asset_id,
            "status": "WOULD_REVIEW" if matches else "EXPECTED_CURRENT_MISMATCH",
            "before": {"lot_size": asset.lot_size, "fractional_support": asset.fractional_support},
            "after": {"lot_size": instruction.evidence.lot_size, "fractional_support": instruction.evidence.fractional_support},
        })
    return MappingProxyType({"supplied": True, "valid": True, "manifest_id": manifest.manifest_id, "instructions": tuple(decisions)})


def _as_aware(value: datetime) -> datetime:
    # SQLAlchemy's existing Asset timestamps are naive UTC.  They are only
    # compared to an explicit manifest snapshot after marking their stored
    # database convention; no current time is inferred here.
    if value.tzinfo is None:
        from datetime import timezone
        return value.replace(tzinfo=timezone.utc)
    return value


def build_lot_capability_preflight(
    db: Session,
    *,
    generated_at: datetime,
    environment_reference: str = "unspecified",
    source_references: Sequence[str] = (),
    manifest: Optional[LotCapabilityManifest] = None,
    authority_trust: Optional[LotCapabilityAuthorityTrust] = None,
    evidence_records: Optional[Mapping[int, Sequence[LotCapabilityEvidence]]] = None,
) -> LotCapabilityPreflightReport:
    """Read Registry state and supplied evidence without resolving symbols or mutating rows."""

    _require_aware(generated_at, "generated_at")
    trust = authority_trust or LotCapabilityAuthorityTrust()
    assets = db.query(Asset).order_by(Asset.id).all()
    asset_map = {int(asset.id): asset for asset in assets}
    try:
        definition_resolver: Optional[BindingResolver] = BindingResolver(DefinitionRegistry.build())
        definition_boot_error: Optional[str] = None
    except DefinitionRegistryError as exc:
        definition_resolver = None
        definition_boot_error = f"{type(exc).__name__}: {exc}"
    identifiers = _current_identifiers_by_asset(db, tuple(asset_map))
    candidates = _candidate_evidence(db, identifiers)
    evidence_by_asset: dict[int, list[LotCapabilityEvidence]] = defaultdict(list)
    for asset_id, records in (evidence_records or {}).items():
        for record in records:
            if int(asset_id) != record.asset_id:
                raise LotCapabilityManifestError("supplied evidence_records key must equal evidence.asset_id")
            evidence_by_asset[int(asset_id)].append(record)
    if manifest is not None:
        for instruction in manifest.instructions:
            evidence_by_asset[instruction.asset_id].append(instruction.evidence)

    rows: list[LotCapabilityAssetReport] = []
    for asset in assets:
        asset_id = int(asset.id)
        current_identifiers = identifiers.get(asset_id, ())
        supplied = tuple(sorted(evidence_by_asset.get(asset_id, ()), key=lambda item: item.evidence_ref))
        lot_allowed, fractional_allowed, definition_error = _definition_permissions(
            asset.asset_type, definition_resolver, definition_boot_error
        )
        identity_matches = tuple(_matches_identity(asset, current_identifiers, item) for item in supplied)
        effective = tuple(_effective_outcome(item, generated_at) for item in supplied)
        evidence_decisions = tuple(
            MappingProxyType({
                "evidence_ref": item.evidence_ref,
                "source_id": item.source_id,
                "source_type": item.source_type.value,
                "source_version": item.source_version,
                "authority": item.authority,
                "confidence": item.confidence.value,
                "approval_state": item.approval_state.value,
                "effective_from": item.effective_from.isoformat(),
                "effective_to": item.effective_to.isoformat() if item.effective_to else None,
                "trusted_authority": trust.accepts(item),
                "identity_match": match,
                "effective_period_result": period.value if period else "CURRENT",
            })
            for item, match, period in zip(supplied, identity_matches, effective)
        )
        conflicting = len({(item.lot_size, item.fractional_support, item.effective_from, item.effective_to) for item in supplied}) > 1
        missing: list[str] = []
        details: list[str] = []
        identity_match: Optional[bool] = None if not supplied else all(identity_matches)
        effective_result = None
        if any(item is not None for item in effective):
            effective_result = next(item.value for item in effective if item is not None)
        governed = any(
            trust.accepts(item)
            and item.confidence == LotCapabilityConfidence.VERIFIED
            and item.approval_state == LotCapabilityApprovalState.APPROVED
            and match
            and outcome is None
            and item.lot_size == asset.lot_size
            and item.fractional_support == asset.fractional_support
            for item, match, outcome in zip(supplied, identity_matches, effective)
        )
        if definition_error:
            outcome = LotCapabilityPreflightOutcome.QUARANTINED
            details.append("Asset Definition consultation failed without fallback")
        elif lot_allowed is not True or fractional_allowed is not True:
            outcome = LotCapabilityPreflightOutcome.DEFINITION_REFINEMENT_NOT_PERMITTED
            missing.append("Asset Definition must permit lot and fractional refinements")
        elif conflicting:
            outcome = LotCapabilityPreflightOutcome.CONFLICT
            details.append("mixed supplied evidence is quarantined; no highest-confidence selection exists")
        elif supplied and not all(identity_matches):
            outcome = LotCapabilityPreflightOutcome.IDENTITY_MISMATCH
            missing.append("explicit identity snapshot must exactly match current Registry identity")
        elif supplied and any(value == LotCapabilityPreflightOutcome.FUTURE_EFFECTIVE for value in effective):
            outcome = LotCapabilityPreflightOutcome.FUTURE_EFFECTIVE
            details.append("future-effective evidence is retained for review but not current")
        elif supplied and any(value == LotCapabilityPreflightOutcome.EXPIRED_EVIDENCE for value in effective):
            outcome = LotCapabilityPreflightOutcome.EXPIRED_EVIDENCE
            details.append("expired evidence is not current")
        elif supplied and any(not trust.accepts(item) for item in supplied):
            outcome = LotCapabilityPreflightOutcome.APPROVAL_REQUIRED
            missing.append("approved authority trust entry")
        elif supplied and any(item.approval_state in {LotCapabilityApprovalState.REJECTED, LotCapabilityApprovalState.QUARANTINED} for item in supplied):
            outcome = LotCapabilityPreflightOutcome.QUARANTINED
            details.append("supplied evidence has a rejected or quarantined governance state")
        elif supplied and any(item.confidence != LotCapabilityConfidence.VERIFIED for item in supplied):
            outcome = LotCapabilityPreflightOutcome.QUARANTINED
            details.append("supplied evidence is not VERIFIED")
        elif supplied:
            outcome = LotCapabilityPreflightOutcome.READY_FOR_REVIEW
            details.append("READY_FOR_REVIEW is non-authoritative and does not enable a write")
        elif asset.fractional_support is False:
            outcome = LotCapabilityPreflightOutcome.UNVERIFIED_DEFAULT
            missing.extend(("governed fractional capability evidence", "governed positive lot_size evidence"))
        else:
            outcome = LotCapabilityPreflightOutcome.MISSING_EVIDENCE
            missing.extend(("governed fractional capability evidence", "governed positive lot_size evidence"))
        if asset.lot_size is None:
            missing.append("current Asset.lot_size is absent")
        elif not isinstance(asset.lot_size, int) or isinstance(asset.lot_size, bool) or asset.lot_size <= 0:
            outcome = LotCapabilityPreflightOutcome.INVALID_VALUE
            missing.append("current Asset.lot_size must be positive integer")
        if not governed:
            missing.append("accepted governed capability evidence")
        rows.append(LotCapabilityAssetReport(
            asset_id=asset_id,
            canonical_symbol=asset.canonical_symbol,
            identifiers=current_identifiers,
            asset_type=asset.asset_type,
            market=asset.market,
            exchange=asset.exchange,
            currency=asset.currency,
            current_lot_size=asset.lot_size,
            current_fractional_support=asset.fractional_support,
            governed_evidence_present=governed,
            lot_refinement_permitted=lot_allowed,
            fractional_refinement_permitted=fractional_allowed,
            definition_consultation_error=definition_error,
            supplied_evidence_refs=tuple(item.evidence_ref for item in supplied),
            supplied_evidence_decisions=evidence_decisions,
            identity_match=identity_match,
            effective_period_result=effective_result,
            conflict=conflicting,
            candidate_operational_evidence=candidates.get(asset_id, LotCapabilityCandidateEvidence("NON_AUTHORITATIVE_CANDIDATE_EVIDENCE", (), ())),
            outcome=outcome,
            missing_requirements=tuple(dict.fromkeys(missing)),
            details=tuple(details),
        ))
    raw = {
        "assets": len(assets),
        "positive_lot_size": sum(isinstance(asset.lot_size, int) and not isinstance(asset.lot_size, bool) and asset.lot_size > 0 for asset in assets),
        "lot_size_missing": sum(asset.lot_size is None for asset in assets),
        "fractional_support_false": sum(asset.fractional_support is False for asset in assets),
    }
    governed_count = sum(row.governed_evidence_present for row in rows)
    outcome_counts = Counter(row.outcome.value for row in rows)
    return LotCapabilityPreflightReport(
        report_version=_REPORT_VERSION,
        generated_at=generated_at,
        environment_reference=_require_text(environment_reference, "environment_reference"),
        source_references=tuple(sorted(_require_text(item, "source_reference") for item in source_references)),
        registry_population_count=len(assets),
        raw_capability_coverage=MappingProxyType(raw),
        governed_evidence_coverage=MappingProxyType({"accepted_capability_evidence": governed_count, "assets_without_accepted_evidence": len(assets) - governed_count}),
        outcome_counts=MappingProxyType(dict(sorted(outcome_counts.items()))),
        assets=tuple(rows),
        manifest_validation=_manifest_validation(manifest, asset_map),
    )
