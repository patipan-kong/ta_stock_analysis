"""The closed, platform-owned vocabulary (asset_definitions.md D3) spelled as
enums for the first time.

No new vocabulary is introduced here — every member below names a word
already declared in a canonical document (docs/definitions/). This module
only gives the words a level-6 Python spelling (constitution Section 7.1),
which is what makes "every declaration's every word is a member of the
closed vocabulary" (M9 TDD Section 6.1) a type-system guarantee instead of a
runtime string comparison: a transcription that misspells a word fails to
import, not fails a boot check.

Adding a member here is a governed vocabulary extension (constitution
Section 8.1 Step 2: behavioral difference, one owning engine, glossary,
DECISION_LOG) — never a routine code change.
"""
from __future__ import annotations

from enum import Enum


class Divisibility(str, Enum):
    """Axis 1 (Unit Semantics) — is quantity discrete or continuous."""

    CONTINUOUS = "CONTINUOUS"
    DISCRETE = "DISCRETE"


class AcquisitionSemantics(str, Enum):
    """Axis 2 (Acquisition Semantics)."""

    NOT_TRANSACTABLE = "NOT_TRANSACTABLE"
    VENUE_TRADED = "VENUE_TRADED"


class SettlementPattern(str, Enum):
    """Axis 3 (Settlement Semantics)."""

    INSTANT = "INSTANT"
    CYCLE_BASED = "CYCLE_BASED"


class ValuationQuestion(str, Enum):
    """Axis 4 (Valuation Semantics) — what question, if any, exists."""

    IDENTITY = "IDENTITY"
    CONTINUOUS_QUOTATION = "CONTINUOUS_QUOTATION"


class FlowType(str, Enum):
    """Axis 5 (Flow Grants) — the closed set of income-flow words."""

    INTEREST = "INTEREST"
    DIVIDEND = "DIVIDEND"


class EventFamily(str, Enum):
    """Axis 6 (Event-Family Grants) — the closed set of structural events."""

    SPLIT = "SPLIT"
    MERGER = "MERGER"
    SPIN_OFF = "SPIN_OFF"
    RENAME = "RENAME"
    SUSPENSION = "SUSPENSION"
    DELISTING = "DELISTING"


class ExistencePattern(str, Enum):
    """Axis 7 (Existence Pattern) — the lifecycle shape of the kind."""

    OPEN_ENDED = "OPEN_ENDED"


class RelationshipKind(str, Enum):
    """Axis 7 — the closed set of permitted relationship kinds a definition
    may grant. Deliberately distinct from services.asset_domain.RelationshipType
    (the Registry's identity-linking vocabulary — DUAL_LISTED, MERGED_INTO,
    ...): that enum names how the Registry links two listing rows: this one
    names which relationship *kinds a definition's Axis 7 grants*, per the
    constitutional documents' own words (asset_definition_equity.md Axis 7).
    Reconciling the two vocabularies is a Registry-domain question, out of
    this milestone's scope (M9 TDD Section 10 does not raise it; noted here
    so the distinction is deliberate, not overlooked).
    """

    SAME_ENTITY = "SAME_ENTITY"
    WRAPS = "WRAPS"
    SUCCESSOR_OF = "SUCCESSOR_OF"
