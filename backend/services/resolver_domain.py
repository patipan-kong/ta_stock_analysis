"""Asset Registry — Identity Resolution vocabulary (Milestone M3).

Extends services/asset_domain.py (M1, untouched) and services/registry_domain.py
(M2, untouched) with the vocabulary needed to resolve external identifiers
into canonical Asset identities. Kept in its own module rather than appended
to either prior file, same rationale as registry_domain.py itself: each
milestone's file stays frozen once shipped.

Confidence is a deterministic classification, not a probability: five
explicit outcomes (RESOLVED / CANDIDATE / AMBIGUOUS / CONFLICT / UNKNOWN),
each reached by rules over identifier-tier evidence — no learned model, no
statistical inference. The weights and thresholds that drive those rules
live in ResolutionPolicy below, not as constants scattered through the
pipeline, so the policy itself can be inspected, tested, and tuned
independently of the mechanics that apply it.

Evidence is kept structured end-to-end (EvidenceContribution,
ContextCorroboration, ClaimIdentifierEvaluation) rather than collapsed into
a prose explanation string — a human-readable explanation is one possible
rendering of this data (see identity_resolver._format_finding_detail for
the one place that currently does that rendering, for the findings audit
trail), not the data's native form.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Mapping, Optional, Tuple

from models.registry_finding import RegistryFinding
from services.asset_domain import AssetId, IdentifierRecord, IdentifierType


class ResolutionVerdict(str, Enum):
    """The five honest positions a resolution can land on
    (ASSET_REGISTRY.md Section 4 / MARKET_DATA_PLATFORM.md Section 5).
    Never guessed past — every claim lands on exactly one of these."""

    RESOLVED = "RESOLVED"      # decisive: identifiers converge on exactly one existing asset
    CANDIDATE = "CANDIDATE"    # decisive-for-new: strong evidence, matches nothing — never auto-minted
    AMBIGUOUS = "AMBIGUOUS"    # insufficient to decide among one or more plausible matches
    CONFLICT = "CONFLICT"      # evidence within the claim itself disagrees, right now
    UNKNOWN = "UNKNOWN"        # nothing matches, nothing strong enough to call it new either


class ResolutionFindingType(str, Enum):
    """finding_type values M3 writes via registry_findings_repository.
    Deliberately not added to registry_domain.FindingType (M2, frozen) —
    RegistryFinding.finding_type is a plain string column, so extending the
    vocabulary a resolver produces does not require touching M2's closed
    minting/attach-time set."""

    RESOLUTION_AMBIGUOUS = "RESOLUTION_AMBIGUOUS"
    RESOLUTION_CONFLICT = "RESOLUTION_CONFLICT"


class AdjudicationDecision(str, Enum):
    """A human's verdict on an open resolution finding. Also used verbatim
    as the persisted `resolution` string (registry_findings_repository.
    resolve_finding takes a plain string) — M2's FindingResolution enum
    (MERGED/CONFIRMED_DISTINCT/DISMISSED) models a different vocabulary
    (mint-time/attach-time findings), not "this claim's identity was
    confirmed", so M3 defines its own rather than overloading M2's."""

    CONFIRM_MATCH = "CONFIRM_MATCH"    # the claim is this existing asset — record the mapping
    CONFIRM_NEW = "CONFIRM_NEW"        # the claim is a genuinely new asset — caller must mint separately
    NOT_A_MATCH = "NOT_A_MATCH"        # none of the candidates are right; no mapping recorded


@dataclass(frozen=True)
class ResolutionPolicy:
    """Deterministic, rules-based configuration driving verdict
    classification. No learned parameters — every field here is a plain
    number or set a human chose and can revise; see ASSET_REGISTRY_
    IMPLEMENTATION_PLAN.md M3 notes for the rationale behind the defaults."""

    identifier_weights: Mapping[IdentifierType, float]
    strong_identifier_types: FrozenSet[IdentifierType]
    historical_multiplier: float
    resolved_threshold: float
    corroboration_bonus: float
    corroboration_penalty: float


DEFAULT_POLICY = ResolutionPolicy(
    # Evidence hierarchy per MARKET_DATA_PLATFORM.md Section 5: ISIN
    # (global, security-granular) > FIGI (listing-granular) > CUSIP/SEDOL
    # (regional) > PROVIDER_SYMBOL (vendor spelling — today's only
    # ticker+exchange evidence; see M3 plan note) > BROKER_CODE (weakest).
    identifier_weights={
        IdentifierType.ISIN: 100.0,
        IdentifierType.FIGI: 90.0,
        IdentifierType.CUSIP: 80.0,
        IdentifierType.SEDOL: 80.0,
        IdentifierType.PROVIDER_SYMBOL: 50.0,
        IdentifierType.BROKER_CODE: 20.0,
    },
    strong_identifier_types=frozenset({
        IdentifierType.ISIN, IdentifierType.CUSIP, IdentifierType.SEDOL, IdentifierType.FIGI,
    }),
    # A uniquely-matching historical mapping must still resolve decisively
    # (ASSET_REGISTRY.md Section 2 — the "ticker retired in 2024, statement
    # imported in 2028" case), so the discount is small, not punitive.
    historical_multiplier=0.95,
    # A single weak-identifier hit (e.g. one broker code) does not clear
    # this bar alone — it lands as AMBIGUOUS rather than being resolved
    # decisively on flimsy evidence.
    resolved_threshold=50.0,
    corroboration_bonus=10.0,
    corroboration_penalty=15.0,
)


@dataclass(frozen=True)
class ResolutionClaim:
    """Unpersisted input to identity_resolver.resolve(). market/exchange/
    currency are corroboration hints only, never matching keys — canonical
    identity is never inferred from ticker+market context alone
    (MARKET_DATA_PLATFORM.md Section 5: evidence flows in, identity flows
    out, the arrow never reverses)."""

    identifiers: Tuple[IdentifierRecord, ...]
    market: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None
    requested_by: Optional[str] = None
    note: Optional[str] = None


@dataclass(frozen=True)
class EvidenceContribution:
    """One claim identifier's scored contribution toward one candidate
    asset."""

    identifier_type: IdentifierType
    identifier_value: str
    is_current: bool
    base_weight: float
    applied_weight: float


@dataclass(frozen=True)
class ContextCorroboration:
    """Result of comparing a claim-supplied market/exchange/currency hint
    against a candidate asset's own field. A secondary, corroborating
    signal only — never itself a match."""

    field: str  # "market" | "exchange" | "currency"
    claim_value: str
    asset_value: Optional[str]
    matched: bool
    applied_weight: float


@dataclass(frozen=True)
class ResolutionCandidate:
    """One asset the claim's evidence points at, with full structured
    provenance for why it scored the way it did."""

    asset_id: AssetId
    score: float
    contributions: Tuple[EvidenceContribution, ...]
    corroborations: Tuple[ContextCorroboration, ...] = ()


@dataclass(frozen=True)
class ClaimIdentifierEvaluation:
    """What happened when one claim identifier was looked up — populated
    for every identifier in the claim regardless of verdict, so CANDIDATE
    vs UNKNOWN is always traceable to concrete evidence rather than
    inferred after the fact."""

    identifier_type: IdentifierType
    identifier_value: str
    is_strong: bool
    hit_count: int


@dataclass(frozen=True)
class ResolutionResult:
    """The resolver's answer to "what asset does this claim represent?".
    candidates is always populated when any evidence matched anything,
    ranked by score descending, regardless of verdict — a RESOLVED result
    still exposes the winning candidate's full contribution breakdown."""

    verdict: ResolutionVerdict
    resolved_asset_id: Optional[AssetId]
    candidates: Tuple[ResolutionCandidate, ...]
    claim_evaluations: Tuple[ClaimIdentifierEvaluation, ...]
    finding: Optional[RegistryFinding] = None
