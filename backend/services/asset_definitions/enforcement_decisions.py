"""Enforcement Boundary Documentation — Stage R1.5 (M13 brief, Sections
"3. Enforcement Boundary Documentation" and "4. Migration Safety Tests").

One hand-authored decision record per AssetType member, classifying why
asset_registry.mint()'s Stage R1 shadow consultation
(`_consult_runtime_for_mint`, M12) agrees or disagrees with the runtime
today, and what Stage R2 should eventually do about it. Per the M13 brief
("No automatic decisions"): this table is authored by a person reviewing
the gap, not derived by scanning code for mismatches — the same discipline
library.py's PINNED_FINGERPRINTS manifest already applies (a fact about
intent, recorded by hand, not a computed fact about the current
transcription).

Two independent axes, matching the brief's two separate sections:
  - GapType      (Section 3) — *why* legacy and runtime agree or disagree.
  - FutureAction (Section 4) — what Stage R2 should eventually do about it.

This module makes no decision by itself and enforces nothing.
test_asset_definitions_enforcement.py keeps it honest against the real
runtime (every AssetType member must have exactly one row; every NO_GAP row
must actually agree with the runtime today; every non-NO_GAP row must
actually disagree) — a change to library.py that quietly adds or removes a
definition will fail that test until this table is updated to match,
which is the "protect migration decisions" property the brief's Section 4
asks for.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

from services.asset_domain import AssetType


class GapType(str, Enum):
    """Why legacy (mint() accepts every AssetType unconditionally) and
    runtime (DefinitionRegistry.exists()) currently agree or disagree.

    NO_GAP is not one of the M13 brief's own four category names (the brief
    only asks to classify *mismatches*) but is needed here for completeness:
    a per-AssetType decision table with no row for the two defined kinds
    would leave "why doesn't this one need a decision" unanswered rather
    than answered.
    """

    NO_GAP                       = "NoGap"
    INTENTIONAL_LEGACY_BEHAVIOR  = "IntentionalLegacyBehavior"
    MISSING_DEFINITION           = "MissingDefinition"
    MIGRATION_REQUIRED           = "MigrationRequired"
    FUTURE_ENFORCEMENT_CANDIDATE = "FutureEnforcementCandidate"


class FutureAction(str, Enum):
    """What Stage R2 should eventually do, once separately authorized
    (M13 brief Section 4). Not acted on by this milestone — see module
    docstring and DECISION_LOG.md's M13 entry."""

    NOT_APPLICABLE = "NotApplicable"
    PRESERVE       = "Preserve"
    MIGRATE        = "Migrate"
    REJECT         = "Reject"


@dataclass(frozen=True)
class EnforcementDecision:
    binding:       str
    consumer:      str
    gap_type:      GapType
    future_action: FutureAction
    rationale:     str
    r2_note:       str


ENFORCEMENT_DECISIONS: Tuple[EnforcementDecision, ...] = (
    EnforcementDecision(
        binding=AssetType.CASH.value,
        consumer="asset_registry.mint()",
        gap_type=GapType.NO_GAP,
        future_action=FutureAction.NOT_APPLICABLE,
        rationale="Cash v1 is defined (M8); legacy and runtime already agree.",
        r2_note="Already safe to enforce with zero behavior change, whenever R2 is authorized.",
    ),
    EnforcementDecision(
        binding=AssetType.EQUITY.value,
        consumer="asset_registry.mint()",
        gap_type=GapType.NO_GAP,
        future_action=FutureAction.NOT_APPLICABLE,
        rationale="Equity v1 is defined (M8); legacy and runtime already agree.",
        r2_note="Already safe to enforce with zero behavior change, whenever R2 is authorized.",
    ),
    EnforcementDecision(
        binding=AssetType.ETF.value,
        consumer="asset_registry.mint()",
        gap_type=GapType.MISSING_DEFINITION,
        future_action=FutureAction.MIGRATE,
        rationale=(
            "ETF's capability shape (venue-traded, cycle-settled, distribution-like flow, "
            "corporate-action events) looks expressible in the existing seven axes without new "
            "vocabulary — closest of the seven gaps to Equity's own shape — but it has not been "
            "authored, reviewed against docs/definitions/asset_definition_library.md's authoring "
            "gates, or fingerprint-pinned."
        ),
        r2_note="Future enforcement candidate once ETF_V1 exists and passes conformance tests.",
    ),
    EnforcementDecision(
        binding=AssetType.FUND.value,
        consumer="asset_registry.mint()",
        gap_type=GapType.MIGRATION_REQUIRED,
        future_action=FutureAction.MIGRATE,
        rationale=(
            "Open-ended/mutual funds are typically NAV-priced, not continuously quoted. "
            "vocabulary.ValuationQuestion currently offers only IDENTITY and CONTINUOUS_QUOTATION "
            "— neither honestly describes NAV pricing — so FUND_V1 likely needs a governed "
            "vocabulary extension (constitution Section 8.1 Step 2) before it can be authored."
        ),
        r2_note="Not a future enforcement candidate until the valuation-axis question is resolved.",
    ),
    EnforcementDecision(
        binding=AssetType.BOND.value,
        consumer="asset_registry.mint()",
        gap_type=GapType.MIGRATION_REQUIRED,
        future_action=FutureAction.MIGRATE,
        rationale=(
            "Bonds carry maturity/coupon-redemption structural events with no analog in the "
            "current EventFamily closed set (SPLIT/MERGER/SPIN_OFF/RENAME/SUSPENSION/DELISTING). "
            "INTEREST already exists as a flow, but the event-family axis likely needs extension "
            "before BOND_V1 can be authored honestly."
        ),
        r2_note="Not a future enforcement candidate until the event-family-axis question is resolved.",
    ),
    EnforcementDecision(
        binding=AssetType.CRYPTO.value,
        consumer="asset_registry.mint()",
        gap_type=GapType.MIGRATION_REQUIRED,
        future_action=FutureAction.MIGRATE,
        rationale=(
            "24/7 markets with no traditional settlement cycle may not cleanly fit "
            "SettlementPattern's INSTANT/CYCLE_BASED dichotomy. Needs domain review before "
            "authoring, not just transcription of an already-agreed shape."
        ),
        r2_note="Not a future enforcement candidate until the settlement-axis fit is confirmed.",
    ),
    EnforcementDecision(
        binding=AssetType.COMMODITY.value,
        consumer="asset_registry.mint()",
        gap_type=GapType.MIGRATION_REQUIRED,
        future_action=FutureAction.MIGRATE,
        rationale=(
            "Physical vs. derivative commodity exposure likely need different acquisition/"
            "settlement/valuation answers, and which one 'COMMODITY' should mean on this platform "
            "is not yet decided — a scope question, not a transcription task."
        ),
        r2_note="Not a future enforcement candidate until platform scope for this kind is decided.",
    ),
    EnforcementDecision(
        binding=AssetType.PROPERTY.value,
        consumer="asset_registry.mint()",
        gap_type=GapType.MIGRATION_REQUIRED,
        future_action=FutureAction.MIGRATE,
        rationale=(
            "Illiquid, appraisal-based valuation has no existing ValuationQuestion member "
            "(only IDENTITY/CONTINUOUS_QUOTATION); PROPERTY_V1 likely needs a governed vocabulary "
            "extension before it can be authored."
        ),
        r2_note="Not a future enforcement candidate until the valuation-axis question is resolved.",
    ),
    EnforcementDecision(
        binding=AssetType.OTHER.value,
        consumer="asset_registry.mint()",
        gap_type=GapType.INTENTIONAL_LEGACY_BEHAVIOR,
        future_action=FutureAction.PRESERVE,
        rationale=(
            "OTHER is the platform's explicit escape hatch for unclassified kinds (M9 TDD "
            "Section 10.2: \"OTHER unregisterable\"). By definition it cannot honestly declare "
            "any axis value, so authoring a definition for it would violate D5 "
            "(declared, never inferred). No future definition is anticipated."
        ),
        r2_note=(
            "R2 must exempt OTHER from any mint-time gate rather than wait for a definition "
            "that cannot exist."
        ),
    ),
)


def decision_for(binding: str) -> EnforcementDecision:
    for decision in ENFORCEMENT_DECISIONS:
        if decision.binding == binding:
            return decision
    raise KeyError(f"no enforcement decision recorded for binding {binding!r}")


def render_text(decisions: Tuple[EnforcementDecision, ...] = ENFORCEMENT_DECISIONS) -> str:
    lines = ["Enforcement Boundary Decisions (Stage R1.5, informational only)", ""]
    for d in decisions:
        lines.append(d.binding)
        lines.append(f"    gap_type:      {d.gap_type.value}")
        lines.append(f"    future_action: {d.future_action.value}")
        lines.append(f"    rationale:     {d.rationale}")
        lines.append(f"    r2_note:       {d.r2_note}")
        lines.append("")
    return "\n".join(lines)
