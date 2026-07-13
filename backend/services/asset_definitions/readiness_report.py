"""Definition Readiness Report — Stage R2 Expansion tooling (M15 brief,
"1. Asset Definition Readiness Analysis" and "4. Enforcement Readiness
Report").

Answers one question per AssetType member, upstream of enforcement
entirely: *could a canonical definition be authored for this binding today,
using only the existing closed vocabulary (vocabulary.py)?* This is a
narrower question than enforcement_decisions.py's FutureAction — a binding
can be MIGRATE (not yet safe to enforce) for two structurally different
reasons, and this module is what tells them apart:

  - the domain model is already expressible; nobody has written and
    reviewed the document yet (VOCABULARY_READY — ETF, per the M13
    rationale's own words: "expressible in the existing seven axes without
    new vocabulary... has not been authored, reviewed... or
    fingerprint-pinned"), versus
  - the domain model itself is incomplete: authoring would require a
    governed vocabulary extension (VOCABULARY_GAP — FUND, BOND, PROPERTY)
    or a platform-scope decision that has nothing to do with vocabulary
    (SCOPE_UNDECIDED — CRYPTO, COMMODITY).

Per the M15 brief ("No automatic decisions"): DEFINITION_READINESS below is
hand-authored, not derived by scanning capability shapes — the same
discipline enforcement_decisions.py already applies to FutureAction, for
the same reason (a computed "this looks similar enough" is a guess dressed
as a fact). generate_enforcement_readiness_report() cross-checks the
authored table against the two things that *are* facts about current code
(library.DEFINITION_LADDERS, enforcement_decisions.ENFORCEMENT_DECISIONS)
so a silent drift between them fails loudly instead of going unnoticed —
see test_definition_readiness.py.

This module makes no decision and enforces nothing. It does not import, and
is not imported by, enforcement_gate.py or asset_registry.py — the M15
brief's "Enforcement isolation" requirement ("No policy preparation changes
affect runtime modes") is satisfied structurally, by this module having no
edge into the mint() call path at all, not by a runtime check.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from services.asset_definitions import library
from services.asset_definitions.enforcement_decisions import (
    ENFORCEMENT_DECISIONS,
    FutureAction,
    decision_for,
)
from services.asset_domain import AssetType


class ReadinessStatus(str, Enum):
    """Whether a canonical definition could be authored for this binding
    today, using only vocabulary.py's existing closed vocabulary."""

    DEFINED           = "Defined"            # CASH, EQUITY — already in library.py
    VOCABULARY_READY  = "VocabularyReady"     # ETF — expressible today, not yet authored
    VOCABULARY_GAP    = "VocabularyGap"       # FUND, BOND, PROPERTY — needs a governed vocabulary extension
    SCOPE_UNDECIDED   = "ScopeUndecided"      # CRYPTO, COMMODITY — needs a platform-scope decision first
    EXEMPT            = "Exempt"              # OTHER — no definition is ever anticipated


@dataclass(frozen=True)
class DefinitionReadiness:
    binding:               str
    status:                ReadinessStatus
    missing_requirements:  Tuple[str, ...]
    note:                  str


# Hand-authored, one row per AssetType member — see module docstring for why
# this is not derived. The prose here is deliberately a narrower restatement
# of enforcement_decisions.py's own `rationale` field, not a new judgment.
DEFINITION_READINESS: Tuple[DefinitionReadiness, ...] = (
    DefinitionReadiness(
        binding=AssetType.CASH.value,
        status=ReadinessStatus.DEFINED,
        missing_requirements=(),
        note="Cash v1 is canonical (M8).",
    ),
    DefinitionReadiness(
        binding=AssetType.EQUITY.value,
        status=ReadinessStatus.DEFINED,
        missing_requirements=(),
        note="Equity v1 is canonical (M8).",
    ),
    DefinitionReadiness(
        binding=AssetType.ETF.value,
        status=ReadinessStatus.VOCABULARY_READY,
        missing_requirements=(
            "authoring: no canonical document drafted",
            "review: asset_definition_library.md §3's mandatory authoring-gate checklist not run",
            "fingerprint: no PINNED_FINGERPRINTS entry",
        ),
        note=(
            "Capability shape (venue-traded, cycle-settled, distribution-like flow, "
            "corporate-action events) looks expressible in the existing seven axes "
            "without a vocabulary extension — the only MIGRATE binding of which that "
            "is true today. Domain-complete in principle; not authored. M15 deliberately "
            "stops here (see DECISION_LOG.md M15 entry) — authoring a canonical, "
            "immutable definition is a human-reviewed step, not a generated one."
        ),
    ),
    DefinitionReadiness(
        binding=AssetType.FUND.value,
        status=ReadinessStatus.VOCABULARY_GAP,
        missing_requirements=(
            "vocabulary: ValuationQuestion has no NAV-pricing member (only IDENTITY, CONTINUOUS_QUOTATION)",
        ),
        note="Open-ended/mutual funds are NAV-priced; needs a governed vocabulary extension before authoring.",
    ),
    DefinitionReadiness(
        binding=AssetType.BOND.value,
        status=ReadinessStatus.VOCABULARY_GAP,
        missing_requirements=(
            "vocabulary: EventFamily has no maturity/coupon-redemption member",
        ),
        note="Bond structural events have no analog in the current closed EventFamily set.",
    ),
    DefinitionReadiness(
        binding=AssetType.CRYPTO.value,
        status=ReadinessStatus.SCOPE_UNDECIDED,
        missing_requirements=(
            "domain review: 24/7, no traditional settlement cycle — fit against "
            "SettlementPattern's INSTANT/CYCLE_BASED dichotomy is unconfirmed",
        ),
        note="Needs domain review of axis fit before it is known whether this is a vocabulary gap at all.",
    ),
    DefinitionReadiness(
        binding=AssetType.COMMODITY.value,
        status=ReadinessStatus.SCOPE_UNDECIDED,
        missing_requirements=(
            "scope decision: physical vs. derivative exposure not yet chosen as what 'COMMODITY' means here",
        ),
        note="A platform-scope question, not a transcription task — unrelated to vocabulary completeness.",
    ),
    DefinitionReadiness(
        binding=AssetType.PROPERTY.value,
        status=ReadinessStatus.VOCABULARY_GAP,
        missing_requirements=(
            "vocabulary: ValuationQuestion has no appraisal-pricing member",
        ),
        note="Illiquid, appraisal-based valuation has no existing ValuationQuestion member.",
    ),
    DefinitionReadiness(
        binding=AssetType.OTHER.value,
        status=ReadinessStatus.EXEMPT,
        missing_requirements=(),
        note="Platform's explicit escape hatch (M9 TDD §10.2); by definition cannot honestly declare any axis.",
    ),
)


def readiness_for(binding: str) -> DefinitionReadiness:
    for row in DEFINITION_READINESS:
        if row.binding == binding:
            return row
    raise KeyError(f"no readiness row recorded for binding {binding!r}")


@dataclass(frozen=True)
class EnforcementReadinessRow:
    """One binding's combined answer to the M15 brief's four questions."""

    binding:                str
    readiness_status:       ReadinessStatus
    future_action:          FutureAction
    safe_to_enforce_today:  bool
    reason:                 str


def generate_enforcement_readiness_report() -> Tuple[EnforcementReadinessRow, ...]:
    """Combines this module's readiness classification with M13's enforcement
    decision table. `safe_to_enforce_today` answers "can ENFORCE mode
    meaningfully affect this binding right now, per already-authorized
    policy?" — true only for FutureAction.REJECT rows (there are none
    today; see enforcement_gate.py), never inferred from readiness alone.
    Readiness informs *whether a future REJECT would be defensible*, not
    whether one exists.
    """
    rows = []
    for member in AssetType:
        readiness = readiness_for(member.value)
        decision = decision_for(member.value)
        safe_to_enforce_today = decision.future_action == FutureAction.REJECT
        rows.append(EnforcementReadinessRow(
            binding=member.value,
            readiness_status=readiness.status,
            future_action=decision.future_action,
            safe_to_enforce_today=safe_to_enforce_today,
            reason=readiness.note,
        ))
    return tuple(rows)


def render_text(rows: Optional[Tuple[EnforcementReadinessRow, ...]] = None) -> str:
    """Human-readable report answering the M15 brief's four questions
    directly: which AssetTypes can safely be enforced, which are blocked by
    missing definitions, which require migration, which are intentionally
    exempt."""
    if rows is None:
        rows = generate_enforcement_readiness_report()

    lines = ["Definition & Enforcement Readiness Report (Stage R2 Expansion, informational only)", ""]

    enforceable = [r for r in rows if r.safe_to_enforce_today]
    vocab_ready = [r for r in rows if r.readiness_status == ReadinessStatus.VOCABULARY_READY]
    blocked = [r for r in rows if r.readiness_status in (ReadinessStatus.VOCABULARY_GAP, ReadinessStatus.SCOPE_UNDECIDED)]
    exempt = [r for r in rows if r.readiness_status == ReadinessStatus.EXEMPT]

    lines.append(f"Safe to enforce today (FutureAction=Reject): {len(enforceable)}")
    for r in enforceable:
        lines.append(f"    {r.binding}")

    lines.append(f"Vocabulary-ready, awaiting authoring: {len(vocab_ready)}")
    for r in vocab_ready:
        lines.append(f"    {r.binding} — {r.reason}")

    lines.append(f"Blocked (definition incomplete): {len(blocked)}")
    for r in blocked:
        lines.append(f"    {r.binding} [{r.readiness_status.value}] — {r.reason}")

    lines.append(f"Intentionally exempt: {len(exempt)}")
    for r in exempt:
        lines.append(f"    {r.binding} — {r.reason}")

    return "\n".join(lines)
