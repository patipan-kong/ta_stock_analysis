# Asset Definition: FUND

_A canonical Asset Definition of the platform library. Governed by [asset_definitions.md](../architecture/asset_definitions.md); authored per [asset_definition_library.md](asset_definition_library.md). Declarations only — no schemas, no code, no metadata, no classification._

| | |
|---|---|
| **Definition** | FUND |
| **Version** | v1 |
| **Status** | Canonical — shipped with the platform (M22) |
| **Individuation (D1)** | Differs from ETF v1 on exactly one axis — Acquisition Semantics (NAV-window subscription/redemption, not venue-traded) |

---

## Purpose

A fund, as this definition describes it, is an open-ended, NAV-priced pooled vehicle acquired and redeemed directly against the issuer at a published net-asset-value — never bought or sold against another holder on a continuous order-book. On every axis but one it behaves exactly as ETF v1 already declares: discrete units, cycle settlement, periodic-NAV valuation, dividend-bearing, the same corporate-action surface, the same relationship kinds. The one place it genuinely differs is *how it changes hands*: an ETF share is bought and sold on a venue; a fund unit is subscribed and redeemed through a NAV window struck against the issuer, with no continuous market standing between buyer and seller.

This document exists because M20's gap analysis found FUND could not yet be authored — not for the reason `readiness_report.py`'s stale rationale claimed (a missing NAV-pricing valuation word; M17 had already shipped `ValuationQuestion.PERIODIC_NAV` for ETF, and the word is binding-agnostic), but for a narrower, different reason: `AcquisitionSemantics` had no word for NAV-window subscription/redemption. Reusing `VENUE_TRADED` would have misdescribed the mechanism (there is no order-book venue) and, worse, would have made FUND byte-identical to ETF_V1 once both share `PERIODIC_NAV` valuation — a D1 violation, the exact mistake M16 made once already for ETF against Equity. M21 closed that gap with `AcquisitionSemantics.NAV_WINDOW`. This document is the definition that word made possible — FUND's own version of the same ladder ETF walked (M16 blocked → M17 vocabulary → M18 authored).

What is *not* this kind, and why the boundary holds without a new declaration:

- **An ETF.** Venue-traded, per ETF v1's own declaration — the two kinds now individuate cleanly on exactly the axis this document adds. A closed-end fund that trades continuously on an exchange with no subscription/redemption mechanism *is* an ETF-shaped instrument under this vocabulary, not a fund — `asset_definition_etf.md`'s own Purpose section already draws this same boundary from the other side.
- **A money-market or private fund with a negotiated, bilateral transfer mechanism.** That is a different acquisition mechanism entirely (private negotiation, not a published NAV window) — M20's gap analysis names this as its own future candidate (`C3`, negotiated acquisition), not this definition's concern.
- **A depositary receipt or wrapper structure.** Equity v1 and ETF v1 already carry this ground via their `WRAPS`/`SAME_ENTITY` relationship grants; this definition grants the same two kinds below for the same reason ETF v1 does, not because fund structures are somehow related to DRs.

---

## Declarations

### Axis 1 — Unit Semantics

**Declared: the unit is one fund unit; quantity is counted in units, whole-unit by default; instances may declare fractional divisibility and lot constraints (permitted refinements, D10); quantity may not be negative.**

Identical to ETF v1's declaration, for the identical reason ETF gives against Equity: a fund unit is issued and redeemed at the subscription/redemption boundary, and fractional allocation at subscription — extremely common in practice, per M20's gap analysis §3.1 — is a channel-level refinement this axis already permits per instance. Nothing about NAV-window acquisition changes what a "unit" *is*; that is Axis 2's declaration, below.

### Axis 2 — Acquisition Semantics

**Declared: NAV-window subscription/redemption.**

The individuating declaration (see Purpose). A fund unit is acquired and disposed of through a periodic net-asset-value window — subscription and redemption struck against the issuer at a published NAV — never a continuous order-book match, and never simply "not transactable" (a fund unit genuinely changes hands; it does so through a different mechanism than a venue). This is `AcquisitionSemantics.NAV_WINDOW`, M21's governed vocabulary extension, used here for the first time by any canonical definition. Distinct from ETF v1's `VENUE_TRADED` (a continuous market matches buyer and seller) and from Cash v1's `NOT_TRANSACTABLE` (no change of hands exists at all).

### Axis 3 — Settlement Semantics

**Declared: cycle-based. The cycle's length is an instance fact.**

A fund subscription or redemption settles some fixed number of days after the NAV strike — pendency between the strike and settlement exists as a distinguishable state, the same `CYCLE_BASED` fact ETF v1 and Equity v1 both already declare, with the cycle's actual length left as an instance refinement per M20's gap analysis §3.1 ("worth confirming at authoring time, not a blocking gap"). Confirmed here: nothing about NAV-window acquisition requires a different settlement mechanism than cycle-based cash movement.

### Axis 4 — Valuation Semantics

**Declared: periodic NAV.**

Identical to ETF v1's declaration — the axis both kinds now genuinely share, per M17's `PERIODIC_NAV` extension and M20's gap analysis (§3.1: "the word `readiness_report.py`'s FUND row still claims is missing... the word itself is binding-agnostic"). A fund's worth, as this definition states it, is established by the same periodic, published net-asset-value calculation ETF v1 already declares — what is declared is only that the NAV question *exists* for this kind, never its arithmetic or publication cadence (D2). Sharing this declaration with ETF v1 is precisely why Axis 2 is the only place this definition may differ, on pain of D1 — the same scalar-vs-set reasoning `asset_definition_etf.md`'s own Axis 4 section already argues applies unchanged here: widening this axis to admit more than one valuation question is a declaration-model change out of this milestone's non-goals, not a decision made quietly inside this document.

### Axis 5 — Flow Grants

**Declared: DIVIDEND. Nothing else.**

Reusing `DIVIDEND` for fund distributions, the same deliberate, non-speculative choice ETF v1 already makes and argues (`asset_definition_etf.md` Axis 5): the closed vocabulary's Axis 5 words today are `INTEREST` and `DIVIDEND` only, there is no separate `DISTRIBUTION` word, and this milestone's non-goals exclude extending the vocabulary to add one. `DIVIDEND` already names the correct economic character — periodic income paid to holders of a pooled vehicle — for both ETF and FUND alike; this is the second consumer of that same reuse decision, not a new one.

`INTEREST` is not granted: a fund holder receives fund distributions, not interest on a balance — the same refusal ETF v1 and Equity v1 both make for the same reason (D7).

### Axis 6 — Event-Family Grants

**Declared: SPLIT, MERGER, SPIN-OFF, RENAME, SUSPENSION, DELISTING.**

Identical to ETF v1's declaration, and for a directly analogous reason: fund mergers and reorganizations are extremely common in practice (a manager absorbing one fund into another is a `MERGER` in this vocabulary's sense, whether or not it is styled a "merger" commercially), fund unit classes are renamed and reorganized, redemption gates and dealing suspensions occur, and outright fund wind-downs are a `DELISTING`-shaped event even though a fund unit has no exchange ticker in the equity sense. Share-price-maintenance splits are less common for NAV-priced units than for venue-traded shares but are not structurally impossible (a unit consolidation or subdivision), so granting the family costs nothing dishonest — ETF v1's own reasoning ("granting a family is a statement that the event is meaningful for the kind, not a prediction any instance will experience it") applies here without modification. Declaring a narrower grant than ETF v1's would not be a more honest definition of this kind — it would be differentiation added for its own sake, which `asset_definition_authoring_guide.md`'s Stage 2 explicitly warns against ("never pad a definition with declarations chosen merely to widen its distance from a neighbor" — read here in reverse: never narrow one for the same reason).

### Axis 7 — Existence Pattern

**Declared: open-ended. May participate in *same-entity*, *wraps*, and *successor-of* relationships; no participation is mandatory.**

Identical to ETF v1's declaration. "Open-ended fund" is, fittingly, the literal fund-structure term as well as this axis's word — M20's gap analysis (§3.1) already confirms this is a clean fit with no gap. The three permitted relationship kinds match lived reality exactly as they do for ETF v1: multiple unit classes of the same fund (*same-entity*), feeder/master fund structures where one vehicle wraps exposure to another (*wraps* — arguably even more common for funds than for ETFs), and fund reorganizations that relaunch a fund as a successor vehicle (*successor-of*, routine via manager rebrand or merger). None is mandatory: a fund that is nobody's twin, wrapper, or successor is a complete instance of the kind — the same "grant what an instance could face, not what is merely conceivable" discipline every prior definition already applies, satisfied here by the same three kinds ETF v1 already established as genuinely load-bearing for a pooled-vehicle structure, not merely inherited without re-argument.

---

## Capability Projection

What an engine holding a FUND instance can learn — the complete truth, nothing else crosses the boundary:

| Query | Answer |
|---|---|
| Unit | one fund unit |
| Quantity | whole-unit default; fractional/lot: instance facts; non-negative |
| Acquisition | NAV-window subscription/redemption |
| Settlement | cycle-based (length: instance fact) |
| Valuation question | periodic NAV |
| Flows admissible | dividend |
| Event families | split, merger, spin-off, rename, suspension, delisting |
| Existence | open-ended; may relate: same-entity, wraps, successor-of |

Compare against [asset_definition_etf.md](asset_definition_etf.md)'s own table: every row is identical except Acquisition — the single declaration this definition exists to make, the same one-axis-diff shape ETF v1 itself established against Equity v1 in M18.

---

## Validation

- **No engine change required.** `capability_view.py` and `governance.py` already treat every `AcquisitionSemantics` member, including `NAV_WINDOW` (M21), generically; no engine branches on this definition's binding. A future subscription/redemption workflow that must strike against a published NAV rather than match a venue order book is what will eventually give this axis's value behavior — this definition only makes the fact declarable and queryable.
- **Constitutional vocabulary only.** Every declaration is a value on one of the seven axes; the one word this document could not have used before M21 (`NAV_WINDOW`) was added as its own separate, governed Step 2 extension — not introduced here.
- **No metadata.** No expense ratios, no share classes, no fund family or issuer name, no AUM, no strategy or benchmark — nothing an engine doesn't branch on appears.
- **No classification.** No market, sector, currency, or domicile occurs anywhere above.
- **No implementation logic.** No NAV formula, no subscription/redemption cut-off arithmetic, no swing-pricing mechanics; the definition grants a valuation *question*, an income *flow*, and an acquisition *mechanism* — their one owning implementation each lives in the engines, none of which exist yet for this kind.

## Related Documents

- [asset_definitions.md](../architecture/asset_definitions.md) — the constitution these declarations are written under
- [asset_definition_library.md](asset_definition_library.md) — the library charter and authoring guide
- [asset_definition_authoring_guide.md](asset_definition_authoring_guide.md) — the eight-stage process this document was authored through
- [asset_definition_etf.md](asset_definition_etf.md) — the sibling this definition differs from by exactly one required axis (Acquisition)
- [asset_model_gap_analysis.md](asset_model_gap_analysis.md) — M20's analysis that located FUND's actual remaining gap (Acquisition, not Valuation) and recommended this as the first binding to close
- [DECISION_LOG.md](../engineering/DECISION_LOG.md) — M17 (periodic NAV vocabulary), M20 (gap analysis), M21 (NAV-window vocabulary extension), M22 (this definition)
