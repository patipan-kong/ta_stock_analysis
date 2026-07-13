# Asset Definition: PROPERTY

_A canonical Asset Definition of the platform library. Governed by [asset_definitions.md](../architecture/asset_definitions.md); authored per [asset_definition_library.md](asset_definition_library.md). Declarations only — no schemas, no code, no metadata, no classification._

| | |
|---|---|
| **Definition** | PROPERTY |
| **Version** | v1 |
| **Status** | Canonical — shipped with the platform (M27) |
| **Individuation (D1)** | Differs from every existing definition on four axes simultaneously — Acquisition (negotiated transfer), Settlement (negotiated closing), Valuation (appraisal-on-event), and Flow Grants (rent) — the largest D1 margin of any definition admitted to the library so far |

---

## Purpose

A property, as this definition describes it, is a bilaterally negotiated, indivisible physical asset: acquired and disposed by case-by-case negotiation rather than through a venue or a NAV window, settled on a closing date that is itself an agreed term of the transaction rather than a standard cycle, valued by a professional appraisal triggered by an event rather than a continuous market or a periodic calculation, and — while held — generates rent rather than a dividend, interest, or coupon. On every other axis it is described by honest absence, not by a word forced to fit: no event families (the corporate-action surface every listed instrument in this library shares has no referent for a physical asset no issuer administers), and an indefinite, open-ended existence (a property does not mature the way a bond does).

This document exists because M20's gap analysis found PROPERTY the most vocabulary-hungry of the five remaining bindings — four axes, not the one-or-two-word pattern ETF (M17→M18), FUND (M21→M22), and BOND (M23→M24) each proved sufficient. M25 designed the four-word bundle in depth, re-validating each gap and stress-testing the bundle as one coherent domain model rather than four independently-optimized words (`property_vocabulary_bundle_design.md`). M26 shipped all four words as one governed vocabulary extension (`AcquisitionSemantics.NEGOTIATED_TRANSFER`, `SettlementPattern.NEGOTIATED_CLOSING`, `ValuationQuestion.APPRAISAL_ON_EVENT`, `FlowType.RENT`). This document is the definition those four words made possible — the same vocabulary-then-authoring ladder every prior binding walked, this time with a four-word bundle shipped together rather than staggered one or two words at a time.

What is *not* this kind, and why the boundary holds without a new declaration:

- **A publicly-traded REIT.** A listed REIT trades on an exchange at a continuously observed price — `VENUE_TRADED` and `CONTINUOUS_QUOTATION`, the same mechanism Equity v1 already declares. It needs none of this bundle and is not this definition (`property_vocabulary_bundle_design.md` §4's own scrutiny of this exact boundary case).
- **A non-traded REIT or open-ended property fund valued at a published NAV.** That is FUND's own acquisition/valuation shape (`NAV_WINDOW` + `PERIODIC_NAV`) — subscription and redemption struck against an issuer at a periodic published price, not a bilaterally negotiated transfer settled on a bespoke closing date. A structure that actually works this way should decline this definition and reuse FUND's, not this one.
- **A bond secured by real estate, or a mortgage-backed instrument.** Both are debt instruments with a continuously observed market price and a contractually-fixed coupon — Bond v1's shape, not this one; the underlying collateral being real property does not change what is actually held and traded.
- **Equity, ETF, or Fund generally.** All three are venue- or NAV-window-acquired, cycle- or NAV-window-settled, and either continuously quoted or periodic-NAV valued — every one of those facts is false for a bilaterally negotiated, appraisal-valued physical asset.

---

## Declarations

### Axis 1 — Unit Semantics

**Declared: the unit is one property; quantity is counted in properties, whole-property only — no fractional or lot refinement is permitted; quantity may not be negative.**

Unlike every other discrete kind in this library (Equity, ETF, Fund, Bond), indivisibility is declared here, not left as a per-instance refinement. `permits_fractional_refinement=False` and `permits_lot_refinement=False` are the definition's own fact about the kind — a property is not divisible into fractional or lot-batched units the way a share or a bond can be, per `property_vocabulary_bundle_design.md` §6's own worked minimal declaration. This is already expressible in today's vocabulary; no new word was needed to say it (fractional real-estate co-ownership platforms, where they exist, are a different, contractually-mediated instrument and would decline this definition rather than stretch it).

### Axis 2 — Acquisition Semantics

**Declared: negotiated transfer.**

The first individuating declaration (see header). A property changes hands through bilateral, case-by-case negotiation between counterparties — no continuous venue matching bids and offers (unlike `VENUE_TRADED`), no periodic published NAV to transact against (unlike `NAV_WINDOW`), and unlike `NOT_TRANSACTABLE` a change of hands genuinely does occur, just never through a venue or a window. `AcquisitionSemantics.NEGOTIATED_TRANSFER` (M26's governed vocabulary extension) is used here for the first time by any canonical definition — the word M25's design document (§2.2, §3) found this axis's confirmed gap and M26 shipped.

### Axis 3 — Settlement Semantics

**Declared: negotiated closing. No cycle-length refinement is permitted — there is no standard cycle for a bespoke process to refine.**

The second individuating declaration. A property's closing date and process are individually agreed per transaction — not a standard fixed-length cycle after trade (unlike `CYCLE_BASED`, refined per-instance in length but structurally the same shape for every trade of the kind) and not instantaneous (unlike `INSTANT`). `permits_cycle_length_refinement=False` for the same reason Cash v1 declares it false for `INSTANT`: the refinement this flag carries only has a referent for a *cycle*, and a negotiated closing is not one — its date is itself a negotiated term, commonly contingent on financing, inspection, or title conditions that can extend or renegotiate the closing itself, not a length to be tuned. `SettlementPattern.NEGOTIATED_CLOSING` (M26's governed vocabulary extension) is used here for the first time.

### Axis 4 — Valuation Semantics

**Declared: appraisal-on-event.**

The third individuating declaration. A property's worth, as this definition states it, is established by a professional appraisal triggered by an event — a sale, a refinancing, a holder-chosen revaluation date — not a continuously observed market price (unlike `CONTINUOUS_QUOTATION`) and not a scheduled, formula-driven periodic calculation (unlike `PERIODIC_NAV`, which presumes a recurring cadence a property appraisal does not have). `ValuationQuestion.APPRAISAL_ON_EVENT` (M26's governed vocabulary extension) is used here for the first time. Per D2, what is declared is only that the appraisal-on-event question exists for this kind — never an appraisal methodology, never a price, never whether a given instance currently has a recent appraisal on file (an instance/Lifecycle fact, not a definitional one).

### Axis 5 — Flow Grants

**Declared: RENT. Nothing else.**

The fourth individuating declaration. A property holder is owed income from a counterparty's continued occupancy or use of the asset under a lease or similar arrangement — `FlowType.RENT` (M26's governed vocabulary extension), used here for the first time by any canonical definition. Distinct from `DIVIDEND` (a discretionary, issuer-declared distribution — a property has no issuer to declare one), `INTEREST` (Cash v1's own balance accrual, never a use-of-asset payment), and `COUPON` (a contractually-fixed yield against a held instrument's principal, with a redemption relationship rent does not have — `property_vocabulary_bundle_design.md` §2.4's own resolution of this exact boundary). Granting any of the three existing words here would misdescribe rent's economic character; `RENT` is the one word that names it truthfully (D7).

### Axis 6 — Event-Family Grants

**Declared: none.**

Honest absence, not an oversight — the same declaration Cash v1 makes and for an analogous reason: the corporate-action surface every listed instrument in this library shares (`SPLIT`, `MERGER`, `SPIN_OFF`, `RENAME`, `SUSPENSION`, `DELISTING`) presumes an issuer administering a listed instrument. A physical property has no issuer, no listing, and no ticker to rename or suspend — none of the six existing event families has a genuine referent here. `asset_definitions.md` §9's own Property walk states this plainly: "no event families." Declaring any of the six for this kind would be exactly the "differentiation added for its own sake" `asset_definition_authoring_guide.md` Stage 2 warns against, in reverse — granting a family with no genuine behavior to admit.

### Axis 7 — Existence Pattern

**Declared: open-ended. No relationship kind is permitted; none is mandatory.**

A property does not mature or expire the way a bond does — `ExistencePattern.OPEN_ENDED`, the same indefinite-horizon fact Cash v1, Equity v1, ETF v1, and Fund v1 all declare, and the constitution's own §9 Property walk states directly ("open-ended existence"). Unlike Equity v1, ETF v1, Fund v1, and Bond v1, no relationship kind is granted here: `SAME_ENTITY` (fungible siblings under one issuer), `WRAPS` (a depositary- or wrapper-structure relationship), and `SUCCESSOR_OF` (a rebrand or reorganization successor) were each grounded, in every prior definition that grants them, in a genuine, presently-anticipated structural fact about listed instruments and their issuers. No such fact is presently being modeled for a bilaterally negotiated physical asset — a property held inside a special-purpose vehicle or exchanged under a like-kind exchange is a real-world possibility, but not one this milestone's brief asks this definition to model, and speculatively granting a relationship kind with no genuine present referent would be exactly the over-differentiation the constitution's own reuse-before-create discipline warns against, applied here in its mirror form (D5 — declared, never inferred; nothing forces a grant before an instance actually demands one, the same restraint Bond v1 applied to a hypothetical perpetual-bond boundary case).

---

## Capability Projection

What an engine holding a PROPERTY instance can learn — the complete truth, nothing else crosses the boundary:

| Query | Answer |
|---|---|
| Unit | one property |
| Quantity | whole-property only; no fractional or lot refinement; non-negative |
| Acquisition | negotiated transfer |
| Settlement | negotiated closing (no cycle-length refinement) |
| Valuation question | appraisal-on-event |
| Flows admissible | rent |
| Event families | none |
| Existence | open-ended; no relationship kind permitted |

Compare against [asset_definition_bond.md](asset_definition_bond.md)'s own table: no row is shared except Existence's open-ended/scheduled-terminal axis label itself, and even there the two definitions' values differ — this is the library's least Equity-shaped definition to date, by design (`property_vocabulary_bundle_design.md` §6's own D1 analysis).

---

## Validation

- **No engine change required.** `capability_view.py`, `governance.py`, and `declarations.py` are already generic over every `AcquisitionSemantics`, `SettlementPattern`, `ValuationQuestion`, and `FlowType` member, including the four M26 added; no engine branches on this definition's binding. A future bilateral-transfer registration workflow, a negotiated-closing booking workflow, an appraisal-intake workflow, and a rent accrual/collection workflow are what will eventually give these declarations behavior — this definition only makes the facts declarable and queryable.
- **Constitutional vocabulary only.** Every declaration is a value on one of the seven axes; the four words this document could not have used before M26 (`NEGOTIATED_TRANSFER`, `NEGOTIATED_CLOSING`, `APPRAISAL_ON_EVENT`, `RENT`) were added as their own separate, governed Step 2 extension — not introduced here. No new vocabulary is introduced by this document (M27's own non-goal).
- **No metadata.** No address, no square footage, no appraised value, no lease terms, no property tax jurisdiction — nothing an engine doesn't branch on appears anywhere above.
- **No classification.** No property type (residential, commercial, industrial), no market, no jurisdiction occurs anywhere above.
- **No implementation logic.** No appraisal methodology, no rent-accrual arithmetic, no closing-contingency mechanics; the definition grants an acquisition *mechanism*, a settlement *pattern*, a valuation *question*, an income *flow*, and existence/event-family *absences* — their one owning implementation each lives in the engines, none of which exist yet for this kind.

## Related Documents

- [asset_definitions.md](../architecture/asset_definitions.md) — the constitution these declarations are written under; §9's Property walk is this document's origin
- [asset_definition_library.md](asset_definition_library.md) — the library charter and authoring guide
- [property_vocabulary_bundle_design.md](property_vocabulary_bundle_design.md) — M25's design of the four-word bundle this document consumes; §6's D1 analysis is this document's individuation argument in full
- [asset_definition_bond.md](asset_definition_bond.md) — the most recent prior canonical definition; the sibling this definition differs from most broadly (four axes, versus Bond's own two against Equity)
- [asset_model_gap_analysis.md](asset_model_gap_analysis.md) — M20's analysis that first located PROPERTY's four-axis gap
- [DECISION_LOG.md](../engineering/DECISION_LOG.md) — M20 (gap analysis), M25 (bundle design), M26 (vocabulary extension), M27 (this definition)
