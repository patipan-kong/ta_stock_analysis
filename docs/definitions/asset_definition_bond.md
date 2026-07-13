# Asset Definition: BOND

_A canonical Asset Definition of the platform library. Governed by [asset_definitions.md](../architecture/asset_definitions.md); authored per [asset_definition_library.md](asset_definition_library.md). Declarations only — no schemas, no code, no metadata, no classification._

| | |
|---|---|
| **Definition** | BOND |
| **Version** | v1 |
| **Status** | Canonical — shipped with the platform (M24) |
| **Individuation (D1)** | Differs from Equity v1 on exactly two axes — Flow Grants (coupon, not dividend) and Existence Pattern (scheduled-terminal, not open-ended) |

---

## Purpose

A bond, as this definition describes it, is a venue-traded, continuously-quoted debt instrument whose holder is owed a periodic, contractually-fixed coupon and, unlike every other kind this library has admitted so far, whose existence is not indefinite: it carries a known-in-advance terminal event (maturity — or, for a callable issue, an early terminal event the issuer may trigger). On four axes it behaves exactly as Equity v1 already declares: discrete units, cycle settlement, the same corporate-action surface, the same permitted relationship kinds. The two places it genuinely differs are *what holding it pays* — a coupon, not a dividend — and *how its story ends* — on a schedule, not indefinitely.

This document exists because M20's gap analysis found BOND could not yet be authored for two, and only two, reasons — both "long anticipated" by the constitution's own §9 Bond walk: `FlowType` had no word for a scheduled, contractually-fixed income character distinct from `DIVIDEND`'s discretionary one, and `ExistencePattern` had no word for a known-in-advance terminal lifecycle distinct from `OPEN_ENDED`'s indefinite one. M23 closed both gaps (`FlowType.COUPON`, `ExistencePattern.SCHEDULED_TERMINAL`). This document is the definition those two words made possible — the same vocabulary-then-authoring ladder ETF (M16→M17→M18) and FUND (M20→M21→M22) each walked, one binding later.

**Resolving the one open question M20's gap analysis flagged and deliberately did not settle** (`asset_model_gap_analysis.md` §3.2: "open question for authoring time whether OTC bond trading is honestly `VENUE_TRADED` or needs the same negotiated-mechanism word Property needs"): this definition declares Axis 2 `VENUE_TRADED`. A bond — whether matched on an exchange order book or quoted and crossed through a dealer network — still changes hands against a counterparty at an observed price, the same "a continuous market matches buyer and seller" mechanism `AcquisitionSemantics.VENUE_TRADED`'s own words describe (`asset_definitions.md` §5.1 axis 2; ETF v1's own Axis 2 section: "the mechanism, never the venue — venues are instance facts"). This is distinct from the *negotiated, bilateral* mechanism Property's own future gap (M20's `C4` candidate) would require — a privately struck transfer with no continuously observable market price at all. A retail OTC bond purchase quoted by a dealer is not that: a price is continuously observable, a counterparty is matched, and the mechanism is the same shape as a listed trade, only the venue's structure differs (dealer network versus central limit order book) — an instance fact, not a definitional one. No new vocabulary is introduced to settle this; the existing word already fits once "venue" is read, as the constitution requires, as a *mechanism* word rather than a *place* word.

What is *not* this kind, and why the boundary holds without a new declaration:

- **An ETF or a fund.** Both are periodic-NAV-valued, pooled, open-ended vehicles (`ValuationQuestion.PERIODIC_NAV`, `ExistencePattern.OPEN_ENDED`) — a bond is a single-issuer debt instrument with a continuously observed market price and a scheduled terminal event, individuating cleanly on both the valuation and existence axes.
- **Equity.** The nearest neighbor on every axis but two (see header). A preferred share with a fixed dividend and no maturity is still equity under this vocabulary, not a bond dressed as one — the absence of `SCHEDULED_TERMINAL` is exactly the fact that keeps it so; a genuinely perpetual bond (rare, but real) would, by the same logic, decline this definition and individuate no differently from equity at all under the current vocabulary, a boundary case this document notes rather than resolves, since no such instance is being modeled today (D5 — declared, never inferred, and nothing forces a perpetual bond to be minted as `BOND` rather than `OTHER` before that question is actually faced).
- **A privately placed, negotiated debt instrument with no continuously observable price** (a bilateral loan, a private note). That is Property's own future acquisition-mechanism gap (`C4`), not this definition's concern — see the Axis 2 resolution above.
- **A money-market instrument valued at a stable NAV.** That is FUND's own acquisition/valuation shape, not this one; a bond's price moves continuously with market conditions, which is exactly what `CONTINUOUS_QUOTATION` (not `PERIODIC_NAV`) declares.

---

## Declarations

### Axis 1 — Unit Semantics

**Declared: the unit is one bond; quantity is counted in bonds, whole-bond by default; instances may declare fractional divisibility and lot constraints (permitted refinements, D10); quantity may not be negative.**

Identical to Equity v1's declaration in shape, though the lot-size refinement this axis permits per instance is, if anything, *more* load-bearing here than for equity: bond markets routinely enforce minimum-denomination lots (e.g. $1,000 or $100,000 face value per unit) far more strictly than equity board lots, and fractional bond investing is a newer, narrower channel than fractional share trading. Both facts are exactly the kind of per-instance refinement this axis already exists to carry (Cash v1's own precedent for D10) — nothing about a bond's debt character changes what a "unit" *is*; that is Axes 4 and 7's declarations, below.

### Axis 2 — Acquisition Semantics

**Declared: venue-traded.**

See Purpose for the full resolution of the OTC-quotation question M20's gap analysis flagged. A bond changes hands against a counterparty at an observed price — the same mechanism Equity v1 and ETF v1 already declare — whether the specific venue is a listed exchange or a dealer network; both are instance facts about market microstructure (Connectivity & Ingestion's provenance concern), never a fact this axis needs a second word to hold.

### Axis 3 — Settlement Semantics

**Declared: cycle-based. The cycle's length is an instance fact.**

A bond trade settles some fixed number of days after execution — pendency between trade and settlement exists as a distinguishable state, the same `CYCLE_BASED` fact Equity v1, ETF v1, and Fund v1 all declare, with the cycle's actual length (bond markets commonly settle T+1 or T+2, sometimes T+3) left as an instance refinement exactly as those three definitions already leave it.

### Axis 4 — Valuation Semantics

**Declared: continuous quotation.**

Not periodic NAV: a bond's worth, as this definition states it, is a continuously observed market price — the same fact Equity v1 declares, and the opposite of ETF v1's and Fund v1's periodic-NAV question. `asset_model_gap_analysis.md` §3.2 confirms this fit directly ("exchange/OTC-quoted bonds fit the existing continuous-quotation word; no new word needed"). What is declared is only that the continuous-quotation question *exists* for this kind — never the arithmetic, never whether a given instance is presently observable (a suspended or defaulted instance with no current quote is degraded observation, Market Intelligence's concern to surface loudly, the same discipline Equity v1's own suspended-instance note already establishes, not a reason to soften this axis).

### Axis 5 — Flow Grants

**Declared: COUPON. Nothing else.**

The individuating declaration this document exists to make, one of two (see header). A bond holder is owed a periodic, contractually-fixed payment — `FlowType.COUPON` (M23's governed vocabulary extension), used here for the first time by any canonical definition. Distinct from `DIVIDEND` (a discretionary, board-declared distribution an issuer may cut, suspend, or omit at will — the character Equity v1, ETF v1, and Fund v1 all grant instead) and from `INTEREST` (Cash v1's own accrual on a balance, never a scheduled payment against a held instrument). Granting `DIVIDEND` here would misdescribe a bond's coupon as discretionary when it is contractually fixed; granting `INTEREST` would misdescribe a held instrument's payment as a balance accrual. `COUPON` is the one existing word that names the correct economic character (D7 — the wrong word here is a wrong fact, not a convenient approximation).

### Axis 6 — Event-Family Grants

**Declared: SPLIT, MERGER, SPIN-OFF, RENAME, SUSPENSION, DELISTING.**

Identical to Equity v1's, ETF v1's, and Fund v1's declaration — deliberately, not by default. M20's gap analysis (§3.2) flagged this axis as an *open question*, noting that `readiness_report.py` and `enforcement_decisions.py` both previously (and, per that same analysis, wrongly) located Bond's blocking gap here ("no maturity/coupon-redemption member") when the constitution's own §9 walk names only the flow and existence axes as required. Checked directly against the existing closed set: a bond's issuer can undergo a `MERGER` (debt assumed by an acquirer, or exchanged for a successor issue — an event that happens *to* a held position, not a acquisition-channel fact), a `RENAME` (issuer or series rename), a `SUSPENSION` (a trading halt), and a `DELISTING` (an exchange-listed bond removed from trading) exactly as an equity issuer can; a `SPLIT`-shaped consolidation of small-denomination notes into a larger one and a `SPIN_OFF`-shaped debt exchange are less common than their equity analogs but not structurally impossible, and this vocabulary's own precedent (ETF v1, Fund v1) is that granting a family is a statement the event is *meaningful for the kind*, never a prediction any instance will experience it. Deliberately **not** declaring a new event family for maturity or an issuer call: `asset_definitions.md` §9's own Bond walk states the maturity/call fact is carried entirely by Axis 7's `SCHEDULED_TERMINAL` existence pattern ("maturity as a known-in-advance terminal status; a call as an early one — both Lifecycle vocabulary the definition merely selects") — a bond reaching or being called to its terminal event is a *lifecycle status transition* (`asset_definitions.md` §5.2's "this bond has matured"), not a *structural event happening to an ongoing position* the way a split or merger is. Introducing a redemption event family here, on top of the existence-pattern declaration already carrying the same fact, would be exactly the "differentiation added for its own sake" `asset_definition_authoring_guide.md` Stage 2 warns against, not an honest second declaration — and this milestone's non-goals forbid extending the vocabulary regardless. The M20/M23 discrepancy this document resolves: the readiness/enforcement tables' old rationale is stale, not the constitution's own analysis.

### Axis 7 — Existence Pattern

**Declared: scheduled-terminal. May participate in *same-entity*, *wraps*, and *successor-of* relationships; no participation is mandatory.**

The second individuating declaration (see header). A bond carries a known-in-advance terminal event — maturity, or an early call — the first use of `ExistencePattern.SCHEDULED_TERMINAL` (M23's governed vocabulary extension) by any canonical definition, distinct from `OPEN_ENDED`'s indefinite horizon that every other current definition (Cash, Equity, ETF, Fund) declares. Per `asset_definitions.md` §5.2's own worked distinction, this declaration states only that the pattern exists — never an instance's actual maturity date (an instance fact) and never whether a given instance has already matured or been called (a Lifecycle status, tracked by Lifecycle & Structural Events, never predicted by this definition).

The three permitted relationship kinds match Equity v1's, ETF v1's, and Fund v1's, for directly analogous reasons rather than by unexamined inheritance: multiple tranches or series issued under one program are *same-entity* (fungible siblings of one issuance, the same fact pattern as multiple equity share classes); a credit-wrapped or third-party-guaranteed bond, or a bond held inside a structured note, is *wraps* (the same relationship kind Equity v1 and Fund v1 grant for depositary-receipt- and fund-of-funds-shaped structures, applied here to a guarantee/wrapper structure instead); a refinancing or exchange offer that relaunches an obligation as a successor issue is *successor-of* (routine in debt markets, the same relationship kind ETF v1 and Fund v1 already grant for provider rebrands and reorganizations). None is mandatory: a standalone bond that is nobody's tranche-sibling, wrapper, or successor is a complete instance of the kind — the same "grant what an instance could face, not what is merely conceivable" discipline every prior definition already applies.

---

## Capability Projection

What an engine holding a BOND instance can learn — the complete truth, nothing else crosses the boundary:

| Query | Answer |
|---|---|
| Unit | one bond |
| Quantity | whole-bond default; fractional/lot: instance facts; non-negative |
| Acquisition | venue-traded |
| Settlement | cycle-based (length: instance fact) |
| Valuation question | continuous quotation |
| Flows admissible | coupon |
| Event families | split, merger, spin-off, rename, suspension, delisting |
| Existence | scheduled-terminal; may relate: same-entity, wraps, successor-of |

Compare against [asset_definition_equity.md](asset_definition_equity.md)'s own table: every row is identical except Flows admissible and Existence — the two declarations this definition exists to make.

---

## Validation

- **No engine change required.** `capability_view.py`, `governance.py`, and `declarations.py`'s `FlowGrants`/`ExistenceDeclaration` are already generic over every `FlowType` and `ExistencePattern` member, including `COUPON` and `SCHEDULED_TERMINAL` (M23); no engine branches on this definition's binding. A future coupon accrual/payment workflow and a future maturity/expiry tracking workflow are what will eventually give these two axes' values behavior — this definition only makes the facts declarable and queryable.
- **Constitutional vocabulary only.** Every declaration is a value on one of the seven axes; the two words this document could not have used before M23 (`COUPON`, `SCHEDULED_TERMINAL`) were added as their own separate, governed Step 2 extension — not introduced here. No new vocabulary is introduced by this document (M24's own non-goal).
- **No metadata.** No coupon rate, no maturity date, no issuer name, no credit rating, no CUSIP/ISIN — nothing an engine doesn't branch on appears anywhere above.
- **No classification.** No market, sector, currency, or seniority tranche occurs anywhere above.
- **No implementation logic.** No coupon-accrual arithmetic, no day-count convention, no yield-to-maturity or present-value formula, no call-schedule mechanics; the definition grants a valuation *question*, an income *flow*, an existence *pattern*, and structural-event *families* — their one owning implementation each lives in the engines, none of which exist yet for this kind.

## Related Documents

- [asset_definitions.md](../architecture/asset_definitions.md) — the constitution these declarations are written under; §9's Bond walk is this document's origin
- [asset_definition_library.md](asset_definition_library.md) — the library charter and authoring guide
- [asset_definition_equity.md](asset_definition_equity.md) — the sibling this definition differs from by exactly two axes
- [asset_definition_etf.md](asset_definition_etf.md) / [asset_definition_fund.md](asset_definition_fund.md) — the periodic-NAV, open-ended siblings this definition is not
- [asset_model_gap_analysis.md](asset_model_gap_analysis.md) — M20's analysis that located BOND's two required words and flagged the Axis 2 question this document resolves
- [DECISION_LOG.md](../engineering/DECISION_LOG.md) — M20 (gap analysis), M23 (coupon/scheduled-terminal vocabulary extension), M24 (this definition)
