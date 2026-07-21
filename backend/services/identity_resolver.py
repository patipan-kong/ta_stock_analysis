"""Asset Registry — Identity Resolution Engine (Milestone M3).

Connects external identifiers to canonical Assets (ASSET_REGISTRY.md
Section 4, MARKET_DATA_PLATFORM.md Section 5). Named identity_resolver, not
symbol_resolver, to avoid collision with the pre-existing, ad hoc
services/symbol_resolver.py (YFINANCE_SYMBOL_MAP + DR-suffix regex) that
this milestone does not touch or wire into — M0_CURRENT_STATE_ANALYSIS.md
identified that module as something a future milestone may retire in favor
of this one, but no such cutover happens here.

Two entry points, matching the mandated separation between Resolve, Mint,
and Adjudicate:

  resolve(db, claim)              -> ResolutionResult
      Read-only. Never creates, merges, or otherwise mutates an Asset.
      Ambiguous/conflicting verdicts are recorded as RegistryFinding rows
      (via registry_findings_repository, unmodified) so the ambiguity is
      durable evidence, not a transient return value.

  adjudicate(db, finding_id, decision, ...) -> RegistryFinding
      The one place a human's decision about an open resolution finding is
      recorded. CONFIRM_MATCH durably records the identifier mapping (via
      registry_service.attach_identifier, unmodified) so the same question
      is never asked twice. CONFIRM_NEW closes the finding but does not
      mint — minting remains a separate, explicit call to
      registry_service.mint_asset by the caller. Never auto-creates, never
      auto-merges.

Reuses M1/M2's existing primitives throughout (ADR-004 — one implementation
per rule): registry_query.find_identifier_rows for candidate matching (the
same current+historical read M2 already built), registry_service.
attach_identifier for recording confirmed mappings, and
registry_findings_repository directly for finding persistence — the same
module registry_service.record_merge itself calls, since M2's
resolve_finding() wrapper is typed to M2's own FindingResolution vocabulary
(MERGED/CONFIRMED_DISTINCT/DISMISSED), which does not model "this claim's
identity was confirmed". Neither services/asset_domain.py (M1) nor
services/registry_domain.py (M2) is modified by this milestone.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Set, Tuple

from sqlalchemy.orm import Session

from models.registry_finding import RegistryFinding
from services import registry_findings_repository as findings_repo
from services import registry_query as query
from services import registry_service
from services.asset_domain import AssetId, IdentifierRecord, IdentifierType
from services.registry_domain import FindingStatus
from services.resolver_domain import (
    AdjudicationDecision,
    ClaimIdentifierEvaluation,
    ContextCorroboration,
    DEFAULT_POLICY,
    EvidenceContribution,
    ResolutionCandidate,
    ResolutionClaim,
    ResolutionFindingType,
    ResolutionPolicy,
    ResolutionResult,
    ResolutionVerdict,
)
from services.registry_service import AssetRegistryError

__all__ = ["resolve", "adjudicate"]


# ── Resolve ──────────────────────────────────────────────────────────────

def resolve(
    db: Session,
    claim: ResolutionClaim,
    *,
    policy: ResolutionPolicy = DEFAULT_POLICY,
    record_finding: bool = True,
) -> ResolutionResult:
    """Resolves a claim against the Registry's current and historical
    identifier evidence. Read-only: never mints, never merges, never
    attaches. AMBIGUOUS/CONFLICT verdicts create a durable finding, unless
    record_finding=False (M37.1 WP2a — Universal Asset Search reusing this
    matching/scoring logic to preview a claim without writing to the
    Registry's findings audit trail; default stays True so every existing
    caller's behavior is unchanged)."""
    claim_evaluations, contributions_by_asset = _match_candidates(db, claim, policy)
    candidates = _score_candidates(db, claim, contributions_by_asset, policy)
    verdict, resolved_asset_id = _classify(claim_evaluations, candidates, policy)

    finding: Optional[RegistryFinding] = None
    if record_finding and verdict in (ResolutionVerdict.AMBIGUOUS, ResolutionVerdict.CONFLICT):
        finding = _record_finding(db, claim, verdict, candidates, policy)

    return ResolutionResult(
        verdict=verdict,
        resolved_asset_id=resolved_asset_id,
        candidates=tuple(candidates),
        claim_evaluations=tuple(claim_evaluations),
        finding=finding,
    )


def _match_candidates(
    db: Session, claim: ResolutionClaim, policy: ResolutionPolicy,
) -> Tuple[List[ClaimIdentifierEvaluation], Dict[int, List[EvidenceContribution]]]:
    claim_evaluations: List[ClaimIdentifierEvaluation] = []
    contributions_by_asset: Dict[int, List[EvidenceContribution]] = defaultdict(list)

    for identifier in claim.identifiers:
        rows = query.find_identifier_rows(db, identifier.identifier_type.value, identifier.value)
        claim_evaluations.append(
            ClaimIdentifierEvaluation(
                identifier_type=identifier.identifier_type,
                identifier_value=identifier.value,
                is_strong=identifier.identifier_type in policy.strong_identifier_types,
                hit_count=len(rows),
            )
        )

        # A current row for this exact (type, value) is the live, decisive
        # fact about who holds it today — it preempts any stale historical
        # rows for that same value (e.g. an asset that once held this value
        # before it was superseded elsewhere). Historical rows only compete
        # with each other when nothing currently claims the value: that is
        # the genuine "recycled identifier, no live claimant" ambiguity
        # ASSET_REGISTRY.md Section 2 expects to be surfaced, not guessed.
        current_rows = [row for row in rows if row.is_current]
        contributing_rows = current_rows or rows

        base_weight = policy.identifier_weights.get(identifier.identifier_type, 0.0)
        seen_assets: Set[int] = set()
        for row in contributing_rows:
            if row.asset_id in seen_assets:
                continue  # one identifier value may have several historical
                # rows on the same asset (re-attached over time); count the
                # identifier's contribution to that asset once.
            seen_assets.add(row.asset_id)
            applied_weight = base_weight if row.is_current else base_weight * policy.historical_multiplier
            contributions_by_asset[row.asset_id].append(
                EvidenceContribution(
                    identifier_type=identifier.identifier_type,
                    identifier_value=identifier.value,
                    is_current=row.is_current,
                    base_weight=base_weight,
                    applied_weight=applied_weight,
                )
            )

    return claim_evaluations, contributions_by_asset


def _score_candidates(
    db: Session,
    claim: ResolutionClaim,
    contributions_by_asset: Dict[int, List[EvidenceContribution]],
    policy: ResolutionPolicy,
) -> List[ResolutionCandidate]:
    candidates: List[ResolutionCandidate] = []
    for raw_asset_id, contributions in contributions_by_asset.items():
        asset_id = AssetId(raw_asset_id)
        corroborations = _corroborate(db, asset_id, claim, policy)
        score = sum(c.applied_weight for c in contributions) + sum(
            c.applied_weight for c in corroborations
        )
        candidates.append(
            ResolutionCandidate(
                asset_id=asset_id,
                score=score,
                contributions=tuple(contributions),
                corroborations=tuple(corroborations),
            )
        )
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


def _corroborate(
    db: Session, asset_id: AssetId, claim: ResolutionClaim, policy: ResolutionPolicy,
) -> List[ContextCorroboration]:
    """Compares claim-supplied market/exchange/currency hints against the
    candidate asset's own fields. Never a matching key on its own — only a
    tie-breaking/corroborating signal (MARKET_DATA_PLATFORM.md Section 5:
    "ticker anchored to an exchange and market is usually decisive", but
    only ever in combination with identifier evidence)."""
    hints = (("market", claim.market), ("exchange", claim.exchange), ("currency", claim.currency))
    if not any(value is not None for _, value in hints):
        return []

    asset = registry_service.get_asset(db, asset_id)
    if asset is None:
        return []

    results: List[ContextCorroboration] = []
    for field_name, claim_value in hints:
        if claim_value is None:
            continue
        asset_value = getattr(asset, field_name)
        matched = asset_value == claim_value
        results.append(
            ContextCorroboration(
                field=field_name,
                claim_value=claim_value,
                asset_value=asset_value,
                matched=matched,
                applied_weight=policy.corroboration_bonus if matched else -policy.corroboration_penalty,
            )
        )
    return results


def _classify(
    claim_evaluations: Sequence[ClaimIdentifierEvaluation],
    candidates: Sequence[ResolutionCandidate],
    policy: ResolutionPolicy,
) -> Tuple[ResolutionVerdict, Optional[AssetId]]:
    if not candidates:
        # Reached only when every claim identifier had zero hits. A strong
        # identifier (ISIN/CUSIP/SEDOL/FIGI) matching nothing is itself
        # clean, corroborated evidence of a genuinely new instrument
        # (ASSET_REGISTRY.md Section 4: "clearly describe something
        # genuinely new"); weak identifiers alone, or no identifiers at
        # all, are not enough to say that with confidence.
        if any(e.is_strong for e in claim_evaluations):
            return ResolutionVerdict.CANDIDATE, None
        return ResolutionVerdict.UNKNOWN, None

    if len(candidates) == 1:
        candidate = candidates[0]
        if candidate.score >= policy.resolved_threshold:
            return ResolutionVerdict.RESOLVED, candidate.asset_id
        return ResolutionVerdict.AMBIGUOUS, None  # single but weak — surfaced, not guessed

    if _has_live_contradiction(candidates):
        return ResolutionVerdict.CONFLICT, None
    return ResolutionVerdict.AMBIGUOUS, None


def _has_live_contradiction(candidates: Sequence[ResolutionCandidate]) -> bool:
    """True when two or more different candidate assets each carry a
    *current* contribution. A given identifier value can only ever be
    current on one asset at a time (registry_service.attach_identifier
    enforces this), so two distinct assets both showing a current
    contribution necessarily means two different identifiers in the same
    claim each authoritatively point somewhere different, right now — a
    live contradiction, not mere historical reuse."""
    assets_with_current = {
        candidate.asset_id for candidate in candidates
        if any(c.is_current for c in candidate.contributions)
    }
    return len(assets_with_current) >= 2


def _record_finding(
    db: Session,
    claim: ResolutionClaim,
    verdict: ResolutionVerdict,
    candidates: Sequence[ResolutionCandidate],
    policy: ResolutionPolicy,
) -> RegistryFinding:
    primary_identifier = max(
        claim.identifiers, key=lambda i: policy.identifier_weights.get(i.identifier_type, 0.0),
    )
    finding_type = (
        ResolutionFindingType.RESOLUTION_CONFLICT
        if verdict == ResolutionVerdict.CONFLICT
        else ResolutionFindingType.RESOLUTION_AMBIGUOUS
    )
    subject, related = candidates[0], (candidates[1] if len(candidates) > 1 else None)

    return findings_repo.create_finding(
        db,
        finding_type=finding_type.value,
        subject_asset_id=subject.asset_id,
        related_asset_id=related.asset_id if related is not None else None,
        identifier_type=primary_identifier.identifier_type.value,
        identifier_value=primary_identifier.value,
        detail=_format_finding_detail(claim, verdict, candidates),
    )


def _format_finding_detail(
    claim: ResolutionClaim, verdict: ResolutionVerdict, candidates: Sequence[ResolutionCandidate],
) -> str:
    """One human-readable rendering of the structured evidence, generated
    for the findings audit trail (RegistryFinding.detail is a plain text
    column). The structured data itself — ResolutionResult.candidates,
    .contributions, .corroborations — is what callers/UIs should build
    their own explanations from; this rendering is not the source of truth."""
    lines = [f"Resolution verdict={verdict.value} over {len(claim.identifiers)} claim identifier(s):"]
    for identifier in claim.identifiers:
        lines.append(f"  - claim identifier {identifier.identifier_type.value}:{identifier.value} (source={identifier.source})")
    lines.append(f"{len(candidates)} candidate asset(s), ranked by score:")
    for candidate in candidates:
        lines.append(f"  - asset_id={candidate.asset_id} score={candidate.score:.1f}")
        for contribution in candidate.contributions:
            lines.append(
                f"      + {contribution.identifier_type.value}:{contribution.identifier_value} "
                f"({'current' if contribution.is_current else 'historical'}) "
                f"weight={contribution.applied_weight:.1f}"
            )
        for corroboration in candidate.corroborations:
            mark = "matched" if corroboration.matched else "mismatched"
            lines.append(
                f"      ~ {corroboration.field} {mark}: claim={corroboration.claim_value!r} "
                f"asset={corroboration.asset_value!r} weight={corroboration.applied_weight:+.1f}"
            )
    return "\n".join(lines)


# ── Adjudicate ───────────────────────────────────────────────────────────

def adjudicate(
    db: Session,
    finding_id: int,
    decision: AdjudicationDecision,
    *,
    asset_id: Optional[AssetId] = None,
    identifiers: Optional[Sequence[IdentifierRecord]] = None,
    resolution_note: str,
    resolved_by: Optional[str] = None,
) -> RegistryFinding:
    """Records a human's decision about an open resolution finding.

    CONFIRM_MATCH requires asset_id and durably attaches the confirmed
    mapping (defaulting to the finding's own identifier_type/value if no
    explicit `identifiers` are given) via registry_service.attach_identifier
    — so a later resolve() call against the same identifier resolves
    decisively without asking again. CONFIRM_NEW and NOT_A_MATCH only close
    the finding; neither mints, merges, nor attaches anything. This
    function never calls mint_asset or record_merge itself."""
    finding = findings_repo.get_finding(db, finding_id)
    if finding is None:
        raise AssetRegistryError(f"no finding with id={finding_id}")

    if decision == AdjudicationDecision.CONFIRM_MATCH:
        if asset_id is None:
            raise AssetRegistryError("CONFIRM_MATCH requires asset_id")
        records = identifiers or (
            IdentifierRecord(
                identifier_type=IdentifierType(finding.identifier_type),
                value=finding.identifier_value,
                source="resolution_adjudication",
            ),
        )
        for record in records:
            registry_service.attach_identifier(db, asset_id, record)

    status = (
        FindingStatus.DISMISSED.value
        if decision == AdjudicationDecision.NOT_A_MATCH
        else FindingStatus.RESOLVED.value
    )
    return findings_repo.resolve_finding(
        db,
        finding,
        status=status,
        resolution=decision.value,
        resolution_note=resolution_note,
        resolved_by=resolved_by,
    )
