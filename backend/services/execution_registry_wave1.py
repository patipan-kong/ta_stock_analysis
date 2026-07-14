"""Deterministic M31.6 evidence dossier for the five Wave 1 symbols.

The collector uses exact stored values only.  It never removes suffixes,
expands aliases, calls a market-data provider, or derives type/market/exchange
from a symbol.  Operational presence is evidence that a symbol needs review;
it is not authority to mint an Asset.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Dict, Mapping, Optional, Sequence, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from models.asset import Asset, AssetIdentifier
from models.database import OptimizerHistory, PortfolioItem, Transaction, Watchlist
from services.asset_domain import IdentifierType

__all__ = [
    "M31_6_WAVE1_SYMBOLS",
    "Wave1Disposition",
    "Wave1RegistryCandidate",
    "Wave1SymbolReview",
    "ExecutionRegistryWave1Manifest",
    "exact_registry_candidates",
    "build_execution_registry_wave1_manifest",
]


M31_6_WAVE1_SYMBOLS: Tuple[str, ...] = (
    "GOOGL01.BK",
    "GULF.BK",
    "ASML01.BK",
    "PLANB.BK",
    "STECON.BK",
)
_ACTIONABLE = frozenset({"BUY", "SELL", "ACCUMULATE", "REDUCE"})
_EXECUTABLE_TRANSACTIONS = frozenset({"BUY", "SELL", "INITIAL_POSITION"})


class Wave1Disposition(str, Enum):
    ALREADY_RESOLVED = "ALREADY_RESOLVED"
    ATTACH_IDENTIFIER_REVIEW_REQUIRED = "ATTACH_IDENTIFIER_REVIEW_REQUIRED"
    QUARANTINE_PENDING_HUMAN_ADJUDICATION = "QUARANTINE_PENDING_HUMAN_ADJUDICATION"


@dataclass(frozen=True)
class Wave1RegistryCandidate:
    asset_id: int
    canonical_symbol: str
    display_symbol: Optional[str]
    asset_type: str
    market: str
    exchange: str
    currency: str
    status: str
    tradable: bool
    identifiers: Tuple[str, ...]
    matched_by: Tuple[str, ...]


@dataclass(frozen=True)
class Wave1SymbolReview:
    requested_symbol: str
    existing_candidates: Tuple[Wave1RegistryCandidate, ...]
    current_identifiers: Tuple[str, ...]
    historical_spellings: Tuple[str, ...]
    current_asset_type: Optional[str]
    evidence_sources: Tuple[str, ...]
    proposed_operation: str
    disposition: Wave1Disposition
    confidence: str
    unresolved_risks: Tuple[str, ...]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["disposition"] = self.disposition.value
        return payload


@dataclass(frozen=True)
class ExecutionRegistryWave1Manifest:
    reviews: Tuple[Wave1SymbolReview, ...]
    instructions: Tuple[Mapping[str, object], ...]

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "milestone": "M31.6",
            "wave": "REGISTRY_REMEDIATION_WAVE_1",
            "scope_symbols": list(M31_6_WAVE1_SYMBOLS),
            "instructions": [dict(item) for item in self.instructions],
            "symbol_reviews": [review.to_dict() for review in self.reviews],
        }


def exact_registry_candidates(
    db: Session,
    requested_symbol: str,
) -> Tuple[Wave1RegistryCandidate, ...]:
    """Return candidates backed by an exact stored value, never a variant."""

    normalized = requested_symbol.strip().upper()
    exact_identifier_rows = (
        db.query(AssetIdentifier)
        .filter(func.upper(AssetIdentifier.value) == normalized)
        .order_by(AssetIdentifier.id)
        .all()
    )
    identifier_asset_ids = {row.asset_id for row in exact_identifier_rows}
    assets = (
        db.query(Asset)
        .filter(
            or_(
                func.upper(Asset.canonical_symbol) == normalized,
                func.upper(func.coalesce(Asset.display_symbol, "")) == normalized,
                Asset.id.in_(identifier_asset_ids) if identifier_asset_ids else False,
            )
        )
        .order_by(Asset.id)
        .all()
    )
    result = []
    for asset in assets:
        identifiers = (
            db.query(AssetIdentifier)
            .filter(AssetIdentifier.asset_id == asset.id)
            .order_by(
                AssetIdentifier.identifier_type,
                AssetIdentifier.value,
                AssetIdentifier.id,
            )
            .all()
        )
        matched_by = []
        if asset.canonical_symbol.strip().upper() == normalized:
            matched_by.append("EXACT_CANONICAL_SYMBOL")
        if (asset.display_symbol or "").strip().upper() == normalized:
            matched_by.append("EXACT_DISPLAY_SYMBOL")
        if any(row.asset_id == asset.id for row in exact_identifier_rows):
            matched_by.append("EXACT_IDENTIFIER_HISTORY")
        result.append(
            Wave1RegistryCandidate(
                asset_id=int(asset.id),
                canonical_symbol=asset.canonical_symbol,
                display_symbol=asset.display_symbol,
                asset_type=asset.asset_type,
                market=asset.market,
                exchange=asset.exchange,
                currency=asset.currency,
                status=asset.status,
                tradable=bool(asset.tradable),
                identifiers=tuple(
                    f"{row.identifier_type}:{row.value};source={row.source};"
                    f"current={str(bool(row.is_current)).lower()}"
                    for row in identifiers
                ),
                matched_by=tuple(matched_by),
            )
        )
    return tuple(result)


def _operational_evidence(db: Session, requested_symbol: str) -> Tuple[str, ...]:
    normalized = requested_symbol.strip().upper()
    evidence = []
    for row in (
        db.query(PortfolioItem)
        .filter(func.upper(PortfolioItem.symbol) == normalized)
        .order_by(PortfolioItem.id)
        .all()
    ):
        evidence.append(
            f"portfolio_items:id={row.id};portfolio_id={row.portfolio_id};"
            f"sector={row.sector or ''};asset_id={row.asset_id or ''}"
        )
    for row in (
        db.query(Watchlist)
        .filter(func.upper(Watchlist.symbol) == normalized)
        .order_by(Watchlist.id)
        .all()
    ):
        evidence.append(
            f"watchlist:id={row.id};workspace_id={row.workspace_id};"
            f"sector={row.sector or ''};asset_id={row.asset_id or ''}"
        )
    for row in (
        db.query(Transaction)
        .filter(
            func.upper(Transaction.symbol) == normalized,
            Transaction.transaction_type.in_(_EXECUTABLE_TRANSACTIONS),
        )
        .order_by(Transaction.id)
        .all()
    ):
        evidence.append(
            f"transactions:id={row.id};type={row.transaction_type};"
            f"currency={row.currency or ''};sector={row.sector or ''};"
            f"asset_id={row.asset_id or ''}"
        )

    latest_by_portfolio: Dict[int, OptimizerHistory] = {}
    for row in (
        db.query(OptimizerHistory)
        .order_by(
            OptimizerHistory.portfolio_id,
            OptimizerHistory.analyzed_at.desc(),
            OptimizerHistory.id.desc(),
        )
        .all()
    ):
        latest_by_portfolio.setdefault(row.portfolio_id, row)
    for portfolio_id, history in sorted(latest_by_portfolio.items()):
        try:
            payload = json.loads(history.result_json or "{}")
        except (TypeError, ValueError):
            continue
        actions = sorted(
            {
                str(allocation.get("action", "")).upper()
                for allocation in payload.get("target_allocations") or ()
                if str(allocation.get("symbol", "")).strip().upper() == normalized
                and str(allocation.get("action", "")).upper() in _ACTIONABLE
            }
        )
        if actions:
            evidence.append(
                f"optimizer_history:id={history.id};portfolio_id={portfolio_id};"
                f"actions={','.join(actions)}"
            )
    return tuple(evidence)


def _review_symbol(db: Session, requested_symbol: str) -> Tuple[Wave1SymbolReview, Optional[dict]]:
    candidates = exact_registry_candidates(db, requested_symbol)
    operational_evidence = _operational_evidence(db, requested_symbol)
    all_identifiers = tuple(
        identifier for candidate in candidates for identifier in candidate.identifiers
    )
    historical_spellings = tuple(
        sorted(
            {
                requested_symbol,
                *(
                    identifier.split(":", 1)[1].split(";", 1)[0]
                    for candidate in candidates
                    for identifier in candidate.identifiers
                ),
            }
        )
    )

    if len(candidates) == 1:
        candidate = candidates[0]
        exact_current_provider = (
            db.query(AssetIdentifier.id)
            .filter(
                AssetIdentifier.asset_id == candidate.asset_id,
                AssetIdentifier.identifier_type == IdentifierType.PROVIDER_SYMBOL.value,
                func.upper(AssetIdentifier.value) == requested_symbol.upper(),
                AssetIdentifier.is_current.is_(True),
            )
            .first()
            is not None
        )
        if exact_current_provider:
            disposition = Wave1Disposition.ALREADY_RESOLVED
            proposed_operation = "NONE"
            confidence = "HIGH"
            risks: Tuple[str, ...] = ()
            instruction = None
        else:
            disposition = Wave1Disposition.ATTACH_IDENTIFIER_REVIEW_REQUIRED
            proposed_operation = "ATTACH_IDENTIFIER"
            confidence = "HIGH"
            risks = (
                "identifier attachment remains unapproved until a Registry steward reviews the exact candidate",
            )
            instruction = {
                "instruction_id": f"m31-6-attach-{requested_symbol.lower()}",
                "requested_symbol": requested_symbol,
                "candidate_asset_ids": [candidate.asset_id],
                "approved": False,
                "operation": "ATTACH_IDENTIFIER",
                "evidence_source": "exact Registry canonical/display/identifier history",
                "evidence_note": (
                    f"exact stored evidence yielded one candidate asset_id={candidate.asset_id}; "
                    "human approval is still required"
                ),
                "asset_id": candidate.asset_id,
                "identifiers": [
                    {
                        "identifier_type": IdentifierType.PROVIDER_SYMBOL.value,
                        "value": requested_symbol,
                        "source": "M31.6 reviewed exact Registry evidence",
                    }
                ],
            }
    else:
        disposition = Wave1Disposition.QUARANTINE_PENDING_HUMAN_ADJUDICATION
        proposed_operation = (
            "ADJUDICATE_AMBIGUOUS_IDENTITY"
            if len(candidates) > 1
            else "MINT_OR_ATTACH_REQUIRES_AUTHORITATIVE_IDENTITY_EVIDENCE"
        )
        confidence = "INSUFFICIENT"
        instruction = None
        if len(candidates) > 1:
            risks = (
                "multiple exact Registry candidates; no candidate may be selected automatically",
            )
        else:
            risks = (
                "no exact Registry candidate",
                "operational presence does not establish asset type",
                "market and exchange are not authoritatively established",
                "minting would require complete explicit identity/type/market/exchange/currency evidence",
            )

    return (
        Wave1SymbolReview(
            requested_symbol=requested_symbol,
            existing_candidates=candidates,
            current_identifiers=all_identifiers,
            historical_spellings=historical_spellings,
            current_asset_type=candidates[0].asset_type if len(candidates) == 1 else None,
            evidence_sources=operational_evidence,
            proposed_operation=proposed_operation,
            disposition=disposition,
            confidence=confidence,
            unresolved_risks=risks,
        ),
        instruction,
    )


def build_execution_registry_wave1_manifest(
    db: Session,
    *,
    symbols: Sequence[str] = M31_6_WAVE1_SYMBOLS,
) -> ExecutionRegistryWave1Manifest:
    """Build an exact-match-only candidate manifest without mutating Registry."""

    normalized = tuple(str(symbol).strip().upper() for symbol in symbols)
    if normalized != M31_6_WAVE1_SYMBOLS:
        raise ValueError("M31.6 Wave 1 scope is fixed to the five approved symbols")
    reviews = []
    instructions = []
    for symbol in M31_6_WAVE1_SYMBOLS:
        review, instruction = _review_symbol(db, symbol)
        reviews.append(review)
        if instruction is not None:
            instructions.append(instruction)
    return ExecutionRegistryWave1Manifest(
        reviews=tuple(reviews),
        instructions=tuple(instructions),
    )
