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
    reviewed the document yet (VOCABULARY_READY — no MIGRATE binding
    qualifies today; see the M16 correction below), versus
  - the domain model itself is incomplete: authoring would require a
    governed vocabulary extension (VOCABULARY_GAP — PROPERTY) or a
    platform-scope decision that has nothing to do with vocabulary
    (SCOPE_UNDECIDED — CRYPTO, COMMODITY).

M16 correction (see DECISION_LOG.md M16 entry): M15 classified ETF
VOCABULARY_READY on the strength of coverage_report.py's capability-shape
prose. M16 attempted to actually author the definition and found that
classification wrong — asset_definitions.md §9's own ETF walk individuates
ETF from Equity by exactly one declaration, periodic-NAV valuation, and
ValuationQuestion has no such member (only IDENTITY, CONTINUOUS_QUOTATION).
Without it, every axis ETF would declare (venue-traded, discrete,
cycle-settled, dividend flow, Equity's corporate-action set, Equity's
relationship set) is identical to Equity v1 — which D1 ("no two definitions
with identical declarations") forbids outright. The lesson generalized:
*readiness* (is the capability shape describable) and *authorability* (does
the declaration set individuate against every existing definition, D1) are
different tests, and only the second one is the one that actually gates
authoring. This module now checks both.

M17 added the missing word (ValuationQuestion.PERIODIC_NAV); M18 (see
DECISION_LOG.md M18 entry) used it to author asset_definition_etf.md and
transcribe ETF_V1 into library.py. ETF's row below transitions from
VOCABULARY_GAP to DEFINED as a direct, hand-updated consequence of that
authoring — not an automatic recomputation, the same discipline every other
row in this table already follows (module docstring, "no automatic
decisions"). test_defined_status_matches_library_ladders is what actually
verifies this row is honest against library.DEFINITION_LADDERS, in both
directions, for every AssetType member.

M20's gap analysis found this module's own FUND row stale: it kept citing a
missing NAV-pricing valuation word after M17 had already shipped
ValuationQuestion.PERIODIC_NAV (for ETF's need, but the word is
binding-agnostic). FUND's real remaining gap was narrower — Axis 2
(Acquisition), not Axis 4 — closed by M21's AcquisitionSemantics.NAV_WINDOW.
M22 (see DECISION_LOG.md M22 entry) used it to author
asset_definition_fund.md and transcribe FUND_V1 into library.py, the same
VOCABULARY_GAP-to-DEFINED transition ETF walked in M18, one binding later.

M20's gap analysis also found this module's own BOND row imprecise: it
named the event-family axis as Bond's gap ("no maturity/coupon-redemption
member"), but the constitution's own §9 Bond walk names the flow axis
(COUPON) and the existence axis (SCHEDULED_TERMINAL) as the two required
words, leaving any event-family question open rather than confirmed. M23
added both words; M24 (see DECISION_LOG.md M24 entry) used them to author
asset_definition_bond.md and transcribe BOND_V1 into library.py — the same
VOCABULARY_GAP-to-DEFINED transition, two bindings later, with no
event-family extension needed after all.

PROPERTY's row named only the Axis 4 (valuation) gap as its blocker — the
same class of staleness M20 found and left uncorrected for FUND's and
BOND's rows in their own turn, because fixing hand-authored rationale text
is in scope only for the milestone that actually closes the gap, not an
earlier analysis or design pass (`property_vocabulary_bundle_design.md` §8
records this explicitly for PROPERTY's own row). M25 designed a four-word
bundle (Acquisition, Settlement, Valuation, Flows); M26 shipped all four
words as one governed vocabulary extension; M27 (see DECISION_LOG.md M27
entry) used them to author asset_definition_property.md and transcribe
PROPERTY_V1 into library.py — the same VOCABULARY_GAP-to-DEFINED
transition, this time closing all four axes at once rather than one or two.

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

    DEFINED           = "Defined"            # CASH, EQUITY, ETF, FUND, BOND — already in library.py
    VOCABULARY_READY  = "VocabularyReady"     # none today — see M16 correction in module docstring
    VOCABULARY_GAP    = "VocabularyGap"       # PROPERTY — needs a governed vocabulary extension
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
        status=ReadinessStatus.DEFINED,
        missing_requirements=(),
        note=(
            "ETF v1 is canonical (M18); individuated from Equity v1 via "
            "ValuationQuestion.PERIODIC_NAV (M17's governed vocabulary extension). "
            "Lineage: M15 wrongly classified this VOCABULARY_READY; M16 attempted "
            "authoring, found it blocked by D1, and corrected the classification to "
            "VOCABULARY_GAP; M17 added the missing vocabulary word; M18 authored the "
            "definition and closed the gap for real."
        ),
    ),
    DefinitionReadiness(
        binding=AssetType.FUND.value,
        status=ReadinessStatus.DEFINED,
        missing_requirements=(),
        note=(
            "Fund v1 is canonical (M22); individuated from ETF v1 via "
            "AcquisitionSemantics.NAV_WINDOW (M21's governed vocabulary extension). "
            "Lineage: this row was stale after M17 (it kept claiming the missing word was a "
            "NAV-pricing valuation member, even after PERIODIC_NAV shipped for ETF); M20's gap "
            "analysis found the real, narrower gap (Axis 2, acquisition); M21 added the missing "
            "vocabulary word; M22 authored the definition and closed the gap for real."
        ),
    ),
    DefinitionReadiness(
        binding=AssetType.BOND.value,
        status=ReadinessStatus.DEFINED,
        missing_requirements=(),
        note=(
            "Bond v1 is canonical (M24); individuated from Equity v1 via FlowType.COUPON and "
            "ExistencePattern.SCHEDULED_TERMINAL (M23's governed vocabulary extensions). "
            "Lineage: this row previously named the event-family axis as the gap ('no "
            "maturity/coupon-redemption member'); M20's gap analysis found that imprecise — the "
            "constitution's own §9 Bond walk names the flow and existence axes instead; M23 added "
            "both missing words and M24 authored the definition, closing the gap for real with no "
            "event-family extension needed."
        ),
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
        status=ReadinessStatus.DEFINED,
        missing_requirements=(),
        note=(
            "Property v1 is canonical (M27); individuated from every existing definition via "
            "AcquisitionSemantics.NEGOTIATED_TRANSFER, SettlementPattern.NEGOTIATED_CLOSING, "
            "ValuationQuestion.APPRAISAL_ON_EVENT, and FlowType.RENT (M26's governed vocabulary "
            "extension, designed in depth by M25). "
            "Lineage: this row previously named only the valuation axis as the gap ('no "
            "appraisal-pricing member'); M20's gap analysis found three more axes (acquisition, "
            "settlement, flows) also missing; M25 designed all four words as one coherent bundle; "
            "M26 shipped the bundle; M27 authored the definition and closed the gap for real — the "
            "largest single vocabulary investment (four words) and the largest D1 margin (four "
            "axes) of any definition admitted to the library so far."
        ),
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
