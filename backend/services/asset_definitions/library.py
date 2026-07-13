"""The loaded library — code-shipped transcriptions of the canonical
Capability Projection tables (M9 TDD Section 1.2: definitions ship inside
the same deployable artifact as the engines that honor them, never as
database rows or runtime-loaded configuration).

Every value below is copied from exactly one row of one document:
  - docs/definitions/asset_definition_cash.md     ("Capability Projection")
  - docs/definitions/asset_definition_equity.md   ("Capability Projection")
  - docs/definitions/asset_definition_etf.md      ("Capability Projection")
  - docs/definitions/asset_definition_fund.md     ("Capability Projection")
  - docs/definitions/asset_definition_bond.md     ("Capability Projection")
  - docs/definitions/asset_definition_property.md ("Capability Projection")

Nothing here reasons about *why* — the "why" lives only in those documents
and is never transcribed (M9 TDD Section 3.1). If a review needs to check
this file against its source, it should be a row-by-row read of the table
above each transcription, which is exactly what
backend/tests/test_asset_definitions_conformance.py automates.

Binding spellings reuse services.asset_domain.AssetType (Reuse Before Create,
ENGINEERING_PRINCIPLES.md) rather than inventing a parallel vocabulary.
CASH, EQUITY, ETF (M18), FUND (M22), BOND (M24), and PROPERTY (M27) are
transcribed here; the other three AssetType members (CRYPTO, COMMODITY,
OTHER) name kinds no canonical definition describes yet (M9 TDD Section
10.2). They are not placeholders and never will silently gain one — a
binding the registry does not carry refuses loudly (DefinitionRegistry.
exists() is False; resolution raises UnresolvedBindingError), never
defaults.

PINNED_FINGERPRINTS is intentionally NOT derived from the transcriptions
below at import time — see fingerprint.py's module docstring for why a
self-referential fingerprint would defeat its own purpose. These digests
were computed once (see the milestone's DECISION_LOG.md entry for how) and
are updated only when a new version is published, by hand, in the same
review that adds the version (M9 TDD Section 5.4).
"""
from __future__ import annotations

from typing import Dict, Tuple

from services.asset_domain import AssetType
from services.asset_definitions.declarations import (
    AcquisitionDeclaration,
    DefinitionTranscription,
    EventFamilyGrants,
    ExistenceDeclaration,
    FlowGrants,
    SettlementDeclaration,
    UnitDeclaration,
    ValuationDeclaration,
)
from services.asset_definitions.vocabulary import (
    AcquisitionSemantics,
    Divisibility,
    EventFamily,
    ExistencePattern,
    FlowType,
    RelationshipKind,
    SettlementPattern,
    ValuationQuestion,
)

CASH_V1 = DefinitionTranscription(
    name="Cash",
    version="v1",
    binding=AssetType.CASH.value,
    source_document="docs/definitions/asset_definition_cash.md",
    effective_from="2026-07-11",  # M8 shipped date — the document's own status line
    unit=UnitDeclaration(
        divisibility=Divisibility.CONTINUOUS,
        quantity_equals_value=True,
        allows_negative=False,
        permits_fractional_refinement=False,  # continuous already; "fractional" is a discrete-unit refinement
        permits_lot_refinement=False,
    ),
    acquisition=AcquisitionDeclaration(semantics=AcquisitionSemantics.NOT_TRANSACTABLE),
    settlement=SettlementDeclaration(pattern=SettlementPattern.INSTANT, permits_cycle_length_refinement=False),
    valuation=ValuationDeclaration(question=ValuationQuestion.IDENTITY),
    flows=FlowGrants(granted=frozenset({FlowType.INTEREST})),
    event_families=EventFamilyGrants(granted=frozenset()),
    existence=ExistenceDeclaration(
        pattern=ExistencePattern.OPEN_ENDED,
        permitted_relationships=frozenset(),
        mandatory_relationships=frozenset(),
    ),
)

EQUITY_V1 = DefinitionTranscription(
    name="Equity",
    version="v1",
    binding=AssetType.EQUITY.value,
    source_document="docs/definitions/asset_definition_equity.md",
    effective_from="2026-07-11",
    unit=UnitDeclaration(
        divisibility=Divisibility.DISCRETE,
        quantity_equals_value=False,
        allows_negative=False,
        permits_fractional_refinement=True,
        permits_lot_refinement=True,
    ),
    acquisition=AcquisitionDeclaration(semantics=AcquisitionSemantics.VENUE_TRADED),
    settlement=SettlementDeclaration(pattern=SettlementPattern.CYCLE_BASED, permits_cycle_length_refinement=True),
    valuation=ValuationDeclaration(question=ValuationQuestion.CONTINUOUS_QUOTATION),
    flows=FlowGrants(granted=frozenset({FlowType.DIVIDEND})),
    event_families=EventFamilyGrants(
        granted=frozenset({
            EventFamily.SPLIT,
            EventFamily.MERGER,
            EventFamily.SPIN_OFF,
            EventFamily.RENAME,
            EventFamily.SUSPENSION,
            EventFamily.DELISTING,
        })
    ),
    existence=ExistenceDeclaration(
        pattern=ExistencePattern.OPEN_ENDED,
        permitted_relationships=frozenset({
            RelationshipKind.SAME_ENTITY,
            RelationshipKind.WRAPS,
            RelationshipKind.SUCCESSOR_OF,
        }),
        mandatory_relationships=frozenset(),
    ),
)

ETF_V1 = DefinitionTranscription(
    name="ETF",
    version="v1",
    binding=AssetType.ETF.value,
    source_document="docs/definitions/asset_definition_etf.md",
    effective_from="2026-07-13",  # M18 shipped date
    unit=UnitDeclaration(
        divisibility=Divisibility.DISCRETE,
        quantity_equals_value=False,
        allows_negative=False,
        permits_fractional_refinement=True,
        permits_lot_refinement=True,
    ),
    acquisition=AcquisitionDeclaration(semantics=AcquisitionSemantics.VENUE_TRADED),
    settlement=SettlementDeclaration(pattern=SettlementPattern.CYCLE_BASED, permits_cycle_length_refinement=True),
    valuation=ValuationDeclaration(question=ValuationQuestion.PERIODIC_NAV),  # the individuating declaration (D1)
    flows=FlowGrants(granted=frozenset({FlowType.DIVIDEND})),
    event_families=EventFamilyGrants(
        granted=frozenset({
            EventFamily.SPLIT,
            EventFamily.MERGER,
            EventFamily.SPIN_OFF,
            EventFamily.RENAME,
            EventFamily.SUSPENSION,
            EventFamily.DELISTING,
        })
    ),
    existence=ExistenceDeclaration(
        pattern=ExistencePattern.OPEN_ENDED,
        permitted_relationships=frozenset({
            RelationshipKind.SAME_ENTITY,
            RelationshipKind.WRAPS,
            RelationshipKind.SUCCESSOR_OF,
        }),
        mandatory_relationships=frozenset(),
    ),
)

FUND_V1 = DefinitionTranscription(
    name="Fund",
    version="v1",
    binding=AssetType.FUND.value,
    source_document="docs/definitions/asset_definition_fund.md",
    effective_from="2026-07-13",  # M22 shipped date
    unit=UnitDeclaration(
        divisibility=Divisibility.DISCRETE,
        quantity_equals_value=False,
        allows_negative=False,
        permits_fractional_refinement=True,
        permits_lot_refinement=True,
    ),
    acquisition=AcquisitionDeclaration(semantics=AcquisitionSemantics.NAV_WINDOW),  # the individuating declaration (D1)
    settlement=SettlementDeclaration(pattern=SettlementPattern.CYCLE_BASED, permits_cycle_length_refinement=True),
    valuation=ValuationDeclaration(question=ValuationQuestion.PERIODIC_NAV),
    flows=FlowGrants(granted=frozenset({FlowType.DIVIDEND})),
    event_families=EventFamilyGrants(
        granted=frozenset({
            EventFamily.SPLIT,
            EventFamily.MERGER,
            EventFamily.SPIN_OFF,
            EventFamily.RENAME,
            EventFamily.SUSPENSION,
            EventFamily.DELISTING,
        })
    ),
    existence=ExistenceDeclaration(
        pattern=ExistencePattern.OPEN_ENDED,
        permitted_relationships=frozenset({
            RelationshipKind.SAME_ENTITY,
            RelationshipKind.WRAPS,
            RelationshipKind.SUCCESSOR_OF,
        }),
        mandatory_relationships=frozenset(),
    ),
)

BOND_V1 = DefinitionTranscription(
    name="Bond",
    version="v1",
    binding=AssetType.BOND.value,
    source_document="docs/definitions/asset_definition_bond.md",
    effective_from="2026-07-13",  # M24 shipped date
    unit=UnitDeclaration(
        divisibility=Divisibility.DISCRETE,
        quantity_equals_value=False,
        allows_negative=False,
        permits_fractional_refinement=True,
        permits_lot_refinement=True,
    ),
    acquisition=AcquisitionDeclaration(semantics=AcquisitionSemantics.VENUE_TRADED),
    settlement=SettlementDeclaration(pattern=SettlementPattern.CYCLE_BASED, permits_cycle_length_refinement=True),
    valuation=ValuationDeclaration(question=ValuationQuestion.CONTINUOUS_QUOTATION),
    flows=FlowGrants(granted=frozenset({FlowType.COUPON})),  # the individuating declaration (D1)
    event_families=EventFamilyGrants(
        granted=frozenset({
            EventFamily.SPLIT,
            EventFamily.MERGER,
            EventFamily.SPIN_OFF,
            EventFamily.RENAME,
            EventFamily.SUSPENSION,
            EventFamily.DELISTING,
        })
    ),
    existence=ExistenceDeclaration(
        pattern=ExistencePattern.SCHEDULED_TERMINAL,  # the other individuating declaration (D1)
        permitted_relationships=frozenset({
            RelationshipKind.SAME_ENTITY,
            RelationshipKind.WRAPS,
            RelationshipKind.SUCCESSOR_OF,
        }),
        mandatory_relationships=frozenset(),
    ),
)

PROPERTY_V1 = DefinitionTranscription(
    name="Property",
    version="v1",
    binding=AssetType.PROPERTY.value,
    source_document="docs/definitions/asset_definition_property.md",
    effective_from="2026-07-13",  # M27 shipped date
    unit=UnitDeclaration(
        divisibility=Divisibility.DISCRETE,
        quantity_equals_value=False,
        allows_negative=False,
        permits_fractional_refinement=False,  # indivisible — the definition's own fact, not an instance refinement
        permits_lot_refinement=False,
    ),
    acquisition=AcquisitionDeclaration(semantics=AcquisitionSemantics.NEGOTIATED_TRANSFER),  # individuating (D1)
    settlement=SettlementDeclaration(pattern=SettlementPattern.NEGOTIATED_CLOSING, permits_cycle_length_refinement=False),  # individuating (D1)
    valuation=ValuationDeclaration(question=ValuationQuestion.APPRAISAL_ON_EVENT),  # individuating (D1)
    flows=FlowGrants(granted=frozenset({FlowType.RENT})),  # individuating (D1)
    event_families=EventFamilyGrants(granted=frozenset()),  # honest absence — no issuer to administer one
    existence=ExistenceDeclaration(
        pattern=ExistencePattern.OPEN_ENDED,
        permitted_relationships=frozenset(),  # no genuinely anticipated relationship kind for this kind today
        mandatory_relationships=frozenset(),
    ),
)

# The version ladder, per definition, ordered ascending by effective_from
# (M9 TDD Section 5.2). Each definition has exactly one rung today — the
# ladder shape exists so a second rung is additive data, not new code.
DEFINITION_LADDERS: Dict[str, Tuple[DefinitionTranscription, ...]] = {
    AssetType.CASH.value: (CASH_V1,),
    AssetType.EQUITY.value: (EQUITY_V1,),
    AssetType.ETF.value: (ETF_V1,),
    AssetType.FUND.value: (FUND_V1,),
    AssetType.BOND.value: (BOND_V1,),
    AssetType.PROPERTY.value: (PROPERTY_V1,),
}

# Pinned expected digests — see module docstring. Populated by running
# fingerprint.compute_fingerprint() against each transcription once, at
# publication time, and hand-copying the result here.
PINNED_FINGERPRINTS: Dict[Tuple[str, str], str] = {
    (AssetType.CASH.value, "v1"): "e69a3c1ae4739ce63587e80dd640dbfc9427152742e9e75b1ebcb6853dcdfb71",
    (AssetType.EQUITY.value, "v1"): "603e6833fd3141f7b495af0dad3d5ae565a01b662e1e66ad2c32be07f84b7305",
    (AssetType.ETF.value, "v1"): "9aeb81273432ba38b0352600b6b786a6afce4c351bcd5247520cadce42a3421d",
    (AssetType.FUND.value, "v1"): "fc5f39514d150ec3fe691d33cdd88b1d3500560fbc0c9a41d7bfff9b21f64841",
    (AssetType.BOND.value, "v1"): "b0f1b2ea41c71eb2d4571b7b4786e884b1c0cb71490d7a1819aa2910b33189ce",
    (AssetType.PROPERTY.value, "v1"): "5533b7cf47a96d241cfbe25dcd89764662f60ca2c4bb4d99d2639577a6a5592f",
}
