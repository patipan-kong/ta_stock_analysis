# Asset Definition: ETF

_A canonical Asset Definition of the platform library. Governed by [asset_definitions.md](../architecture/asset_definitions.md); authored per [asset_definition_library.md](asset_definition_library.md). Declarations only — no schemas, no code, no metadata, no classification._

| | |
|---|---|
| **Definition** | ETF |
| **Version** | v1 |
| **Status** | Canonical — shipped with the platform (M18) |
| **Individuation (D1)** | Differs from Equity v1 on exactly one axis — Valuation Semantics (periodic NAV, not continuous quotation) |

---

## Purpose

An ETF is a venue-traded fund share: on every axis but one, it behaves exactly as Equity v1 already declares — discrete units, cycle settlement, dividend-bearing, the same corporate-action surface, the same relationship kinds. The one place it genuinely differs is *how its worth is established*: an ETF's authoritative value is a periodically published net-asset-value calculation, not a continuously observed market print. This document exists because M16 attempted to author ETF as a distinct kind and found it could not be — the vocabulary had no word for that difference, so every axis ETF would have declared collapsed onto Equity v1's actual declarations, which D1 (no two definitions with identical declarations) forbids. M17 added the missing word, `ValuationQuestion.PERIODIC_NAV` ([asset_definitions.md](../architecture/asset_definitions.md) §9's own ETF walk names it). This document is the definition that word made possible.

The constitution's own ETF walk (§9) observes that a real ETF is arguably worth asking about *both* ways — continuously quoted intraday on its listing venue, and periodically NAV-priced at its authorized-participant creation/redemption boundary — and notes "either answer is a healthy outcome" for how a v1 declaration resolves that. This definition resolves it toward periodic NAV, deliberately, for two reasons:

- **The axis is a single question, not a set.** Axis 4 ([declarations.py](../../backend/services/asset_definitions/declarations.py) `ValuationDeclaration`) holds one `ValuationQuestion`, the same scalar shape Cash and Equity already use — unlike Axis 5/6's flow and event-family grants, which are genuinely sets. Widening Axis 4 to a set is a real option for some future version, but it is a vocabulary/declaration-model change this milestone's non-goals explicitly exclude ("do not extend vocabulary further," "do not redesign runtime") — not a decision to make quietly inside a definition's authoring.
- **NAV is the more fundamental fact for this kind.** Creation and redemption — the mechanism that keeps an ETF's market price tethered to its holdings — happens at NAV; continuous intraday quotation is the secondary, market-observed consequence of that tether holding, the same relationship Cash's Axis 4 reasoning already draws between "quantity ≡ value" (the fact) and any derived reporting-currency conversion (not a fact about the instance). If a future need genuinely requires modeling intraday quotation as an *independent* second valuation fact — arbitrage-gap analytics, say — that is an honest widening, argued openly as a new version (§8.2), not assumed here.

What is *not* this kind, and why the boundary holds without a new declaration:

- **A closed-end fund.** Trades continuously with no creation/redemption mechanism tying price to NAV — Equity v1's own declaration (continuous quotation, nothing more) already describes it; giving it this definition would falsify the NAV grant.
- **An open-ended mutual fund with no venue listing.** NAV-priced, correctly, but not venue-traded — Axis 2 (Acquisition Semantics) would have to read `NOT_TRANSACTABLE` or something between the two current words, which is FUND's own, separate `VOCABULARY_GAP` (`readiness_report.py`), not this definition's concern.
- **A depositary receipt or dual-listed equity.** Equity v1 already carries this ground via its `WRAPS`/`SAME_ENTITY` relationship grants; an ETF's own use of those same relationship kinds (below) is the same fact pattern, not evidence the two kinds should merge.

---

## Declarations

### Axis 1 — Unit Semantics

**Declared: the unit is one share; quantity is counted in shares, whole-share by default; instances may declare fractional divisibility and lot constraints (permitted refinements, D10); quantity may not be negative.**

Identical to Equity v1's declaration, for the identical reason: an ETF share is issued and redeemed in whole units at the creation/redemption boundary, and secondary-market fractional trading is a channel-level refinement this axis already permits per instance — the same divisibility story Equity v1 tells for board lots and tenth-shares. Nothing about fund structure changes what a "unit" *is*.

### Axis 2 — Acquisition Semantics

**Declared: venue-traded.**

An ETF share changes hands on an exchange exactly as a listed equity does. The creation/redemption mechanism — authorized participants exchanging baskets for creation units — is not a second acquisition mechanism *of this kind*: it is how the venue-traded supply is manufactured, a fact about market microstructure and Connectivity & Ingestion's provenance concerns (per Equity v1's own "private placements" reasoning), never a fact a holder's transaction records need a different word for. A retail buy of an ETF share is indistinguishable, at this axis, from a retail buy of a listed share.

### Axis 3 — Settlement Semantics

**Declared: cycle-based. The cycle's length is an instance fact.**

An ETF trade settles on the same venue convention a listed equity trade does — pendency between trade and settlement exists as a distinguishable state, and which cycle governs is instance-refined exactly as Equity v1 declares.

### Axis 4 — Valuation Semantics

**Declared: periodic NAV.**

The individuating declaration (see Purpose). An ETF's worth, as this definition states it, is established by a periodic, published net-asset-value calculation — the fact Market Intelligence answers for this kind, distinct from Equity v1's continuous quotation (a fixed face amount answered by nobody, Cash's declaration, is not a candidate here at all). What is declared is only that the NAV question *exists* for this kind — never its arithmetic, its publication cadence, or which venue's intraday print an engine might also observe (D2, valuation mathematics never enters a definition). A suspended or halted instance with no current NAV publication is degraded observation, Market Intelligence's concern to surface loudly — not a reason to soften this axis, the same discipline Equity v1's suspended-instance note already establishes.

### Axis 5 — Flow Grants

**Declared: DIVIDEND. Nothing else.**

The closed vocabulary's Axis 5 words today are `INTEREST` and `DIVIDEND` — there is no separate `DISTRIBUTION` word in `vocabulary.py`, even though Equity v1's own document anticipates one in prose ("distribution is the fund-character income word; dividend is the equity-character one"). That sentence describes a distinction the vocabulary has not yet been asked to make: no fund-shaped kind existed to test it until now, and this milestone's non-goals exclude extending the vocabulary to add it. Reusing `DIVIDEND` here is therefore not a synonym collision (there is nothing to collide with) but a deliberate, honest choice of the one existing word that already names this economic character — periodic income paid to holders of a pooled vehicle. If a future milestone genuinely needs to distinguish equity-character income from fund-character income for tax or reporting purposes, that is its own governed Step 2 vocabulary extension (adding `DISTRIBUTION`), argued on its own need — not invented here to make this document look more precise than the vocabulary currently is.

`INTEREST` is not granted: an ETF's holders receive fund distributions, not interest on a balance — the same refusal Equity v1 makes for the same reason (D7: withholding forces a misclassified import to surface at the gate, not land silently).

### Axis 6 — Event-Family Grants

**Declared: SPLIT, MERGER, SPIN-OFF, RENAME, SUSPENSION, DELISTING.**

The same six families Equity v1 grants, because ETFs genuinely undergo all six in practice: reverse splits (share-price maintenance), fund mergers and reorganizations (extremely common — a provider absorbing one fund into another is a `MERGER`, in this vocabulary's sense, whether or not it is styled a "merger" commercially), rare multi-fund spin-offs, ticker and name changes, trading suspensions, and outright fund closures (`DELISTING`). Granting a family is a statement that the event is *meaningful for the kind* (Equity v1's own reasoning), not a prediction any instance will experience it — the same honest-grant-now, process-later posture Equity v1 takes for its own quantitative families still awaiting Phase 5's admission pipeline.

Not granted: **redemption** as a per-instance corporate action — an ETF share is not issuer-redeemed on an individual holder's schedule the way a bond might be; the creation/redemption mechanism is Axis 2's acquisition/disposal channel, not a structural event happening *to* a held position. **Expiry** and **exercise** are not granted for the same reason Equity v1 withholds them: nothing about an ETF share ends or converts by contract.

### Axis 7 — Existence Pattern

**Declared: open-ended. May participate in *same-entity*, *wraps*, and *successor-of* relationships; no participation is mandatory.**

An ETF share has no scheduled end — "open-ended" is, fittingly, the literal fund-structure term as well as this axis's word. The three permitted relationship kinds match lived reality: cross-listed or dual-share-class ETFs (*same-entity*), feeder/wrapper fund structures where one vehicle wraps exposure to another (*wraps* — the same relationship kind Equity v1 grants for depositary receipts, applied here to fund-of-funds structures rather than DR-to-underlying), and fund reorganizations that relaunch a fund as a successor vehicle (*successor-of* — routine in the ETF industry via provider rebrand/relaunch). None is mandatory: an ETF that is nobody's twin, wrapper, or successor is a complete instance of the kind.

---

## Capability Projection

What an engine holding an ETF instance can learn — the complete truth, nothing else crosses the boundary:

| Query | Answer |
|---|---|
| Unit | one share |
| Quantity | whole-share default; fractional/lot: instance facts; non-negative |
| Acquisition | venue-traded |
| Settlement | cycle-based (length: instance fact) |
| Valuation question | periodic NAV |
| Flows admissible | dividend |
| Event families | split, merger, spin-off, rename, suspension, delisting |
| Existence | open-ended; may relate: same-entity, wraps, successor-of |

Compare against [asset_definition_equity.md](asset_definition_equity.md)'s own table: every row is identical except Valuation question — the single declaration this definition exists to make.

---

## Validation

- **No engine change required.** `capability_view.py` and `governance.py` already treat every `ValuationQuestion` member, including `PERIODIC_NAV`, generically (M17); no engine branches on this definition's binding. A future Market Intelligence pricing engine that fetches NAV data on a publication schedule rather than a continuous feed is what will eventually give this axis's value behavior — this definition only makes the fact declarable and queryable.
- **Constitutional vocabulary only.** Every declaration is a value on one of the seven axes; the one word this document could not have used before M17 (`PERIODIC_NAV`) was added as its own separate, governed Step 2 extension — not introduced here.
- **No metadata.** No expense ratios, no index tracked, no fund family or issuer name, no AUM — nothing an engine doesn't branch on appears.
- **No classification.** No market, sector, currency, exchange, or share-class name occurs anywhere above.
- **No implementation logic.** No NAV formula, no creation-unit arithmetic, no arbitrage-band mathematics; the definition grants a valuation *question*, an income *flow*, and structural-event *families* — their one owning implementation each lives in the engines, none of which exist yet for this kind.

## Related Documents

- [asset_definitions.md](../architecture/asset_definitions.md) — the constitution these declarations are written under; §9's ETF walk is this document's origin
- [asset_definition_library.md](asset_definition_library.md) — the library charter and authoring guide
- [asset_definition_equity.md](asset_definition_equity.md) — the sibling this definition differs from by exactly one axis
- [ASSET_REGISTRY.md](../architecture/ASSET_REGISTRY.md) — the listing as the unit of identity; lifecycle statuses; relationships
- [DECISION_LOG.md](../engineering/DECISION_LOG.md) — M16 (blocked attempt), M17 (vocabulary extension), M18 (this definition)
