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
        gap_type=GapType.FUTURE_ENFORCEMENT_CANDIDATE,
        future_action=FutureAction.MIGRATE,
        rationale=(
            "ETF_V1 was authored and fingerprint-pinned in M18 (see DECISION_LOG.md), after M17's "
            "vocabulary extension (ValuationQuestion.PERIODIC_NAV) made it individuable from "
            "Equity v1 under D1. asset_registry.mint()'s shadow consultation now genuinely agrees "
            "with the runtime for this binding — the gap this table originally recorded "
            "(MISSING_DEFINITION) has closed. future_action is deliberately left at MIGRATE, not "
            "promoted to NOT_APPLICABLE: a definition existing is necessary but not sufficient for "
            "an enforcement policy decision, which remains a separate, explicit, human-led step "
            "(M18 brief's own non-goal: 'do not enable additional enforcement')."
        ),
        r2_note="Realized: ETF_V1 exists and passes conformance tests. Awaiting a separate, explicit R2 authorization to promote past MIGRATE.",
    ),
    EnforcementDecision(
        binding=AssetType.FUND.value,
        consumer="asset_registry.mint()",
        gap_type=GapType.FUTURE_ENFORCEMENT_CANDIDATE,
        future_action=FutureAction.MIGRATE,
        rationale=(
            "FUND_V1 was authored and fingerprint-pinned in M22 (see DECISION_LOG.md), after M21's "
            "vocabulary extension (AcquisitionSemantics.NAV_WINDOW) made it individuable from ETF v1 "
            "under D1. asset_registry.mint()'s shadow consultation now genuinely agrees with the "
            "runtime for this binding — the gap this table originally recorded (MIGRATION_REQUIRED, "
            "on what M20's gap analysis later showed was the wrong axis: valuation, not acquisition) "
            "has closed. future_action is deliberately left at MIGRATE, not promoted to "
            "NOT_APPLICABLE: a definition existing is necessary but not sufficient for an enforcement "
            "policy decision, which remains a separate, explicit, human-led step (M22 brief's own "
            "non-goal: 'do not change enforcement policy'), the same posture ETF's row took in M18."
        ),
        r2_note="Realized: FUND_V1 exists and passes conformance tests. Awaiting a separate, explicit R2 authorization to promote past MIGRATE.",
    ),
    EnforcementDecision(
        binding=AssetType.BOND.value,
        consumer="asset_registry.mint()",
        gap_type=GapType.FUTURE_ENFORCEMENT_CANDIDATE,
        future_action=FutureAction.MIGRATE,
        rationale=(
            "BOND_V1 was authored and fingerprint-pinned in M24 (see DECISION_LOG.md), after M23's "
            "vocabulary extension (FlowType.COUPON, ExistencePattern.SCHEDULED_TERMINAL) made it "
            "individuable from Equity v1 under D1. asset_registry.mint()'s shadow consultation now "
            "genuinely agrees with the runtime for this binding — the gap this table originally "
            "recorded (MIGRATION_REQUIRED, on what M20's gap analysis later showed was the wrong "
            "axis: event families, not flow/existence) has closed. future_action is deliberately "
            "left at MIGRATE, not promoted to NOT_APPLICABLE: a definition existing is necessary but "
            "not sufficient for an enforcement policy decision, which remains a separate, explicit, "
            "human-led step (M24 brief's own non-goal: 'do not enable enforcement'), the same "
            "posture ETF's and FUND's rows took in M18/M22."
        ),
        r2_note="Realized: BOND_V1 exists and passes conformance tests. Awaiting a separate, explicit R2 authorization to promote past MIGRATE.",
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
        gap_type=GapType.FUTURE_ENFORCEMENT_CANDIDATE,
        future_action=FutureAction.MIGRATE,
        rationale=(
            "PROPERTY_V1 was authored and fingerprint-pinned in M27 (see DECISION_LOG.md), after "
            "M25 designed and M26 shipped a four-word governed vocabulary extension "
            "(AcquisitionSemantics.NEGOTIATED_TRANSFER, SettlementPattern.NEGOTIATED_CLOSING, "
            "ValuationQuestion.APPRAISAL_ON_EVENT, FlowType.RENT) that made it individuable from "
            "every existing definition under D1. asset_registry.mint()'s shadow consultation now "
            "genuinely agrees with the runtime for this binding — the gap this table originally "
            "recorded (MIGRATION_REQUIRED, naming only the valuation axis) has closed. "
            "future_action is deliberately left at MIGRATE, not promoted to NOT_APPLICABLE: a "
            "definition existing is necessary but not sufficient for an enforcement policy "
            "decision, which remains a separate, explicit, human-led step (M27 brief's own "
            "non-goal: 'do not enable enforcement'), the same posture ETF's, FUND's, and BOND's "
            "rows took in M18/M22/M24."
        ),
        r2_note="Realized: PROPERTY_V1 exists and passes conformance tests. Awaiting a separate, explicit R2 authorization to promote past MIGRATE.",
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
