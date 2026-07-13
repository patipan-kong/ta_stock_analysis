"""The closed, platform-owned vocabulary (asset_definitions.md D3) spelled as
enums for the first time.

Almost every member below names a word already declared in a canonical
document (docs/definitions/) — this module gives such words a level-6 Python
spelling (constitution Section 7.1), which is what makes "every
declaration's every word is a member of the closed vocabulary" (M9 TDD
Section 6.1) a type-system guarantee instead of a runtime string comparison:
a transcription that misspells a word fails to import, not fails a boot
check.

Adding a member here is a governed vocabulary extension (constitution
Section 8.1 Step 2: behavioral difference, one owning engine, glossary,
DECISION_LOG) — never a routine code change. `ValuationQuestion.PERIODIC_NAV`
(M17) is this module's first genuine Step 2 addition: the word was named in
prose by the constitution itself (asset_definitions.md §9's ETF walk) before
any canonical document's Capability Projection table used it — no definition
transcribes it yet (library.py still ships only CASH_V1/EQUITY_V1), so it
exists here purely as an available word, not yet a declared fact about any
kind.
"""
from __future__ import annotations

from enum import Enum


class Divisibility(str, Enum):
    """Axis 1 (Unit Semantics) — is quantity discrete or continuous."""

    CONTINUOUS = "CONTINUOUS"
    DISCRETE = "DISCRETE"


class AcquisitionSemantics(str, Enum):
    """Axis 2 (Acquisition Semantics) — the mechanism by which instances are
    acquired and disposed.

    NAV_WINDOW added M21 (governed vocabulary extension per
    asset_definitions.md §8.1 Step 2 — see DECISION_LOG.md M21 entry):
    acquisition and disposal through a periodic net-asset-value window —
    subscription and redemption struck against the issuer at a published
    NAV, never a continuous order-book match. Distinct from VENUE_TRADED
    (a continuous market matches buyer and seller) and NOT_TRANSACTABLE (no
    change of hands exists at all) — per asset_definitions.md §5.1 axis 2's
    own worked phrase ("venue-traded, NAV-window subscription/redemption,
    negotiated private transfer, or not transactable at all") and the M20
    gap analysis (asset_model_gap_analysis.md §3.1), this is the word that
    lets a NAV-window-acquired kind (fund) individuate from a
    venue-traded, periodic-NAV-valued kind (ETF) without collapsing to an
    identical declaration set (D1) now that both already share
    ValuationQuestion.PERIODIC_NAV. Owning engine: Asset Foundation
    (asset_definitions.md §5.1 axis 2 — the mint/registration path that
    knows how an instance actually changes hands, distinct from Market
    Intelligence's axis-4 valuation question). No engine branches on this
    value today — the word is declarative vocabulary only, per D2; a future
    subscription/redemption workflow is what will eventually behave
    differently because of it.

    NEGOTIATED_TRANSFER added M26 (governed vocabulary extension per
    asset_definitions.md §8.1 Step 2 — see DECISION_LOG.md M26 entry,
    implementing the bundle M25 designed): acquisition and disposal by
    bilateral, case-by-case negotiation between counterparties — no
    continuous venue matching bids and offers (unlike VENUE_TRADED), no
    periodic published NAV to transact against (unlike NAV_WINDOW), and
    unlike NOT_TRANSACTABLE a change of hands does occur, just never
    through a venue or a window. Per asset_definitions.md §5.1 axis 2's own
    worked phrase ("venue-traded, NAV-window subscription/redemption,
    negotiated private transfer, or not transactable at all") and the M20
    gap analysis (asset_model_gap_analysis.md §3.3, concept C3), this is
    the word that lets a bilaterally-negotiated kind (property) individuate
    from every acquisition mechanism above. Owning engine: Asset Foundation
    (the same owner named for NAV_WINDOW). No engine branches on this value
    today — the word is declarative vocabulary only, per D2; a future
    bilateral-transfer registration workflow is what will eventually behave
    differently because of it. Reusable beyond Property by any future kind
    whose acquisition is genuinely bespoke and bilateral rather than venue-
    or NAV-window-mediated — see property_vocabulary_bundle_design.md §4.
    """

    NOT_TRANSACTABLE = "NOT_TRANSACTABLE"
    VENUE_TRADED = "VENUE_TRADED"
    NAV_WINDOW = "NAV_WINDOW"
    NEGOTIATED_TRANSFER = "NEGOTIATED_TRANSFER"


class SettlementPattern(str, Enum):
    """Axis 3 (Settlement Semantics) — when a change of hands becomes real.

    NEGOTIATED_CLOSING added M26 (governed vocabulary extension per
    asset_definitions.md §8.1 Step 2 — see DECISION_LOG.md M26 entry,
    implementing the bundle M25 designed): a settlement date and process
    individually agreed per transaction — not a standard fixed-length cycle
    after trade (unlike CYCLE_BASED, which is refined per-instance in
    length but is structurally the same shape for every trade of the kind),
    and not instantaneous (unlike INSTANT). Per asset_definitions.md §5.1
    axis 3 and the M20 gap analysis (asset_model_gap_analysis.md §3.3,
    concept C4), this is the word that lets a bespoke-negotiated closing
    (property) individuate from a standard settlement cycle without
    collapsing to an identical declaration set (D1). Owning engine: Ledger
    & Accounting (the subdomain that books a change of hands as real; the
    same owner that already consumes INSTANT/CYCLE_BASED). No engine
    branches on this value today — the word is declarative vocabulary only,
    per D2; a future negotiated-closing booking workflow is what will
    eventually behave differently because of it. Reusable beyond Property
    by any future kind whose settlement date is itself a bilaterally
    negotiated term rather than a standard cycle — see
    property_vocabulary_bundle_design.md §4.
    """

    INSTANT = "INSTANT"
    CYCLE_BASED = "CYCLE_BASED"
    NEGOTIATED_CLOSING = "NEGOTIATED_CLOSING"


class ValuationQuestion(str, Enum):
    """Axis 4 (Valuation Semantics) — what question, if any, exists.

    PERIODIC_NAV added M17 (governed vocabulary extension per
    asset_definitions.md §8.1 Step 2 — see DECISION_LOG.md M17 entry): a
    periodic, published net-asset-value calculation. Distinct from IDENTITY
    (worth is a fixed face amount; no calculation exists) and
    CONTINUOUS_QUOTATION (worth is a continuously observed market price) —
    per asset_definitions.md §9's own ETF walk, this is the word that lets
    a periodic-NAV kind individuate from a continuously-quoted one without
    collapsing to an identical declaration set (D1). Owning engine: Market
    Intelligence (asset_definitions.md §5.1 axis 4; §6.2 "to know what
    identified things are worth"). No engine branches on this value today —
    the word is declarative vocabulary only, per D2; a future Market
    Intelligence pricing engine is what will eventually behave differently
    because of it.

    APPRAISAL_ON_EVENT added M26 (governed vocabulary extension per
    asset_definitions.md §8.1 Step 2 — see DECISION_LOG.md M26 entry,
    implementing the bundle M25 designed): worth is established by a
    professional appraisal triggered by an event (a sale, a refinancing, a
    holder-chosen revaluation date) — a third, distinct question-shape from
    CONTINUOUS_QUOTATION (a continuously observed market price) and
    PERIODIC_NAV (a scheduled, formula-driven periodic calculation): an
    appraisal has no continuous market and no fixed recurring cadence, only
    an event-triggered professional judgment. Per asset_definitions.md
    §5.1.4's own phrase ("continuous quotation, periodic NAV,
    appraisal-on-event, or identity") and the M20 gap analysis
    (asset_model_gap_analysis.md §3.3, concept C2), this is the word that
    lets an appraisal-valued kind (property) individuate from every
    existing valuation question. Owning engine: Market Intelligence (the
    same owner named for CONTINUOUS_QUOTATION and PERIODIC_NAV). No engine
    branches on this value today — the word is declarative vocabulary only,
    per D2; a future appraisal-intake workflow is what will eventually
    behave differently because of it. Reusable beyond Property by any
    future kind valued through event-triggered professional judgment rather
    than a market or a formula — see property_vocabulary_bundle_design.md
    §4, the bundle's highest-confidence reuse candidate.
    """

    IDENTITY = "IDENTITY"
    CONTINUOUS_QUOTATION = "CONTINUOUS_QUOTATION"
    PERIODIC_NAV = "PERIODIC_NAV"
    APPRAISAL_ON_EVENT = "APPRAISAL_ON_EVENT"


class FlowType(str, Enum):
    """Axis 5 (Flow Grants) — the closed set of income-flow words.

    COUPON added M23 (governed vocabulary extension per asset_definitions.md
    §8.1 Step 2 — see DECISION_LOG.md M23 entry): a periodic,
    contractually-fixed income flow — distinct from DIVIDEND (a
    discretionary, board-declared distribution an issuer may cut, suspend,
    or omit) and from INTEREST (Cash v1's own accrual on a balance, not a
    scheduled payment against a held instrument). Per asset_definitions.md
    §5.1 axis 5's own phrase ("dividend, coupon, interest, rent, staking
    reward, distribution — each carrying its income character") and §9's
    own Bond walk ("the coupon flow type — one owner: the accounting
    implementation that admits it"), and the M20 gap analysis
    (asset_model_gap_analysis.md §3.2, §5 concept C6), this is the word
    that lets a bond's scheduled fixed payment be admitted by the ledger
    without borrowing DIVIDEND's discretionary character or INTEREST's
    balance-accrual character. Owning engine: Ledger & Accounting
    (asset_definitions.md §5.1 axis 5; §5.2's "a definition says a coupon
    is admissible; whether one occurred is forever the ledger's fact"). No
    engine branches on this value today — the word is declarative
    vocabulary only, per D2; a future coupon accrual/payment workflow is
    what will eventually behave differently because of it. Reusable
    beyond Bond by any future kind with a contractually-fixed, scheduled
    income character (e.g. private debt).

    RENT added M26 (governed vocabulary extension per asset_definitions.md
    §8.1 Step 2 — see DECISION_LOG.md M26 entry, implementing the bundle
    M25 designed): a holding-generated income flow arising from a
    counterparty's continued occupancy or use of a physical asset under a
    lease or similar arrangement — distinct from DIVIDEND (discretionary,
    issuer-declared), INTEREST (balance accrual), and COUPON (a
    contractually-fixed yield against a held instrument's principal, with a
    redemption relationship rent does not have). Per asset_definitions.md
    §5.1.5 and §9's own Property walk, and the M20 gap analysis
    (asset_model_gap_analysis.md §3.3, concept C7), this is the word that
    lets a property's rental income be admitted by the ledger without
    borrowing DIVIDEND's discretionary character, INTEREST's
    balance-accrual character, or COUPON's principal/redemption character.
    Owning engine: Ledger & Accounting (the same owner named for
    COUPON/DIVIDEND/INTEREST). No engine branches on this value today — the
    word is declarative vocabulary only, per D2; a future rent
    accrual/collection workflow is what will eventually behave differently
    because of it. Confirmed Property-only by the M20/M25 reuse analysis,
    with a tentative, unconfirmed Infrastructure usage-fee case noted for
    completeness — see property_vocabulary_bundle_design.md §4.
    """

    INTEREST = "INTEREST"
    DIVIDEND = "DIVIDEND"
    COUPON = "COUPON"
    RENT = "RENT"


class EventFamily(str, Enum):
    """Axis 6 (Event-Family Grants) — the closed set of structural events."""

    SPLIT = "SPLIT"
    MERGER = "MERGER"
    SPIN_OFF = "SPIN_OFF"
    RENAME = "RENAME"
    SUSPENSION = "SUSPENSION"
    DELISTING = "DELISTING"


class ExistencePattern(str, Enum):
    """Axis 7 (Existence Pattern) — the lifecycle shape of the kind.

    SCHEDULED_TERMINAL added M23 (governed vocabulary extension per
    asset_definitions.md §8.1 Step 2 — see DECISION_LOG.md M23 entry): a
    lifecycle with a known-in-advance terminal event — a bond's maturity,
    an option's expiry — distinct from OPEN_ENDED's indefinite horizon.
    Per asset_definitions.md §5.1 axis 7's own phrase ("the lifecycle
    pattern the kind follows (open-ended; scheduled-terminal like a bond's
    maturity or an option's expiry)") and §9's own Bond walk, and the M20
    gap analysis (asset_model_gap_analysis.md §3.2, §5 concept C8 —
    "highest reuse value of any candidate identified"), this is the word
    that lets a maturity/expiry-shaped kind (bond) individuate from an
    indefinite-life kind (every currently canonical definition) without a
    new axis. The definition declares only that a terminal event exists in
    the pattern — never an instance's actual maturity date (an instance
    fact) or whether that instance has already matured (a Lifecycle
    status) — per asset_definitions.md §5.2's own "Bonds mature" / "this
    bond matures 2031-03-15" / "this bond has matured" distinction. Owning
    engine: Lifecycle & Structural Events (asset_definitions.md §5.1
    axis 7 — "drawn from Lifecycle's vocabulary"; §5.3's "Lifecycle
    positions" ruling that only the *pattern*, never any instance's
    position in it, is definitional). No engine branches on this value
    today — the word is declarative vocabulary only, per D2; a future
    maturity/expiry tracking workflow is what will eventually behave
    differently because of it.
    """

    OPEN_ENDED = "OPEN_ENDED"
    SCHEDULED_TERMINAL = "SCHEDULED_TERMINAL"


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
