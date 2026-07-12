# Asset Definition: Equity

_A canonical Asset Definition of the platform library. Governed by [asset_definitions.md](../architecture/asset_definitions.md); authored per [asset_definition_library.md](asset_definition_library.md). Declarations only — no schemas, no code, no metadata, no classification._

| | |
|---|---|
| **Definition** | Equity |
| **Version** | v1 |
| **Status** | Canonical — shipped with the platform |
| **Individuation (D1)** | No other definition declares this contract |

---

## Purpose

Equity is an exchange-listed ownership share: the kind the platform was born holding, and the kind whose behavior the engines' accumulated correctness was hardened against. Its definition is the richest text in the v1 library — the most flows, the most event families, the most instance-refined declarations — which is exactly why it belongs in the founding pair: if the vocabulary can carry the platform's most exercised kind without remainder, the contract is real.

The unit of identity is the **listing** ([ASSET_REGISTRY.md](../architecture/ASSET_REGISTRY.md) §5), and this definition describes the listed share as a kind. Three things it deliberately does **not** distinguish, because they are not behavioral differences (D1):

- **Markets.** A Thai bank share and a US technology share make identical declarations on every axis. Market, currency, and venue are instance facts and classification — one definition serves both, which is the entire point.
- **Common vs. preferred.** A preferred share is venue-traded, dividend-paying, corporate-actionable, cycle-settled — the same contract. Its preference is a classification fact (income character, seniority), not a kind.
- **Depositary receipts.** A DR trades, pays, splits, and settles exactly as this definition declares. What makes it a DR is a *wraps* relationship to its underlying and a classification fact — never a separate definition. The platform's oldest identity scar (DR symbol entanglement) is answered here by refusing to let the wrapper become a kind.

What is *not* this kind: an unlisted private share. Negotiated acquisition and appraisal valuation are different declarations on two axes — a genuinely different behavior contract, arriving later as its own definition (the Business walk in the constitution's §9), never as a variant of this one.

---

## Declarations

### Axis 1 — Unit Semantics

**Declared: the unit is one share; quantity is counted in shares, whole-share by default; instances may declare fractional divisibility and lot constraints (permitted refinements, D10); quantity may not be negative; share count changes only through recorded transactions and adjudicated structural events.**

- *The share.* Ownership is denominated in issued units, not weight or face amount; conservation is conservation of share count against the ledger.
- *Whole by default, fractional by instance declaration.* The kind-level truth is that divisibility varies by venue and channel: Thai listings trade in board lots; some US channels book tenth-shares. Declaring "discrete, always" would falsify real holdings; declaring "continuous" would falsify the unit. The constitutional resolution is D10 used as designed: the definition **permits** the refinement, and each instance declares its own fractional allowance and lot size within that permission. An instance claiming a refinement this axis did not permit — negative quantity, say — is a registration-time defect.
- *Non-negative.* v1 declares no short selling. A negative share count is not a smaller holding but a **borrowed** one — different conservation, different obligations. If the platform ever supports shorting, sign is a definitional widening: a new version, openly argued (§8.2). Until then the accounting core refuses the state, and this declaration is its authority.

### Axis 2 — Acquisition Semantics

**Declared: venue-traded.**

Challenged: *should equity always be venue-traded?* For this kind — yes, and the edge cases dissolve under the platform's own laws rather than weakening the declaration:

- *"What about a delisted share I still hold?"* Lifecycle, not acquisition. Delisted-but-held is a position with a status ([ASSET_REGISTRY.md](../architecture/ASSET_REGISTRY.md) §6); the kind's acquisition mechanism never changed — there is simply no venue on which to exercise it *going forward*. The definition says how the kind changes hands; lifecycle says whether this instance can, today.
- *"What about off-market block transfers?"* An in-kind TRANSFER is already universal vocabulary — custody movement, not an acquisition mechanism of the kind.
- *"What about private placements of listed shares?"* The acquired thing is still the listed share; the unusual door is Connectivity & Ingestion's concern (provenance), not a second mechanism.
- What would genuinely break the declaration — a share that *only* changes hands by negotiation — is not this kind (see Purpose).

### Axis 3 — Settlement Semantics

**Declared: cycle-based. The cycle's length is an instance fact.**

A trade and its reality are separated by the venue's settlement convention. Which convention — T+2, T+1, tomorrow's inevitable T+0 — belongs to the instance and its market, refining this declaration (D10). The kind-level fact engines rely on is only that pendency *exists*: settled and unsettled are distinguishable states for this kind, which is precisely what cash, instant by declaration, does not have.

### Axis 4 — Valuation Semantics

**Declared: continuous quotation.**

The kind can be asked "what is this worth now?" whenever its venue is open, and daily closes are the same question at coarser cadence — one declaration covers both, because cadence within continuous quotation is an observation-availability matter for Market Intelligence, not a second valuation kind. What is **not** declared: periodic NAV (that is the fund-shaped question; a kind that answers both is the ETF discussion, deferred to its own definition per the constitution's §9), and appraisal (the unlisted world's question). A suspended instance with no quotes today is degraded observation, loudly surfaced by Market Intelligence — never a reason to soften this axis.

### Axis 5 — Flow Grants

**Declared: DIVIDEND. Nothing else.**

Challenged, in both directions:

- *Should equity support interest?* **No — and the refusal is the feature.** Interest is the income character of lending and cash-like holding. When a broker statement shows "interest" on a stock account, that flow belongs to the account's **cash** instance (which grants it), not to the shares. Granting interest here would give a misclassified import somewhere legitimate to land; withholding it forces the booking error to surface at the gate, loudly, where it is corrected instead of absorbed (D7). A definition is as valuable for what it refuses as for what it admits.
- *Should equity grant distribution?* No. Distribution is the fund-character income word; dividend is the equity-character one. One meaning, one word — granting both to the same kind for the same economics would begin the synonym rot the vocabulary rules exist to prevent (§7.2).
- *What about stock dividends and bonus shares?* Not flows at all: a share count change decreed by the issuer is a **structural event** (Axis 6's split family of consequences), not holding income. The two axes must not blur — money arrives on Axis 5; quantity restructuring arrives on Axis 6.
- *Dividend, granted unconditionally.* A never-paying growth stock still holds the grant: the mechanism exists for the kind. Whether any instance pays is history (the ledger's), never definition.

### Axis 6 — Event-Family Grants

**Declared: SPLIT, MERGER, SPIN-OFF, RENAME, SUSPENSION, DELISTING.**

The full listed-share event surface — the quantitative families (split, merger, spin-off) and the venue-life families (rename, suspension, delisting) the platform's lifecycle machinery already exercises.

Challenged: *may a definition grant families the platform cannot yet process end-to-end?* The quantitative families' ledger consequences await Phase 5's admission pipeline — yet they are granted now, deliberately. A grant declares that the event is **meaningful for the kind**: a split *can happen* to a listed share, as a fact about the world, independent of the platform's current processing depth. Refusing the grant would falsify the kind to flatter a roadmap. The gap is honest and owned elsewhere: an announced split today is interpreted and recorded by Lifecycle & Structural Events, and its consequences wait at the gate — degraded loudly, per the crossing contract ([asset_foundation.md](../architecture/asset_foundation.md) §4.4), never silently. What the grant forbids is only the *surprise*: no engine may treat a split against an equity as structurally inadmissible.

Not granted: **redemption** (a common share is not issuer-redeemed on schedule; a buyback is a SELL, a squeeze-out is the merger family), **expiry** and **exercise** (nothing about a share ends or converts by contract — those words wait for the derivative kinds that need them).

### Axis 7 — Existence Pattern

**Declared: open-ended. May participate in *same-entity*, *wraps*, and *successor-of* relationships; no participation is mandatory.**

A share has no scheduled end; its story closes, when it closes, through Axis 6's families and the lifecycle statuses they set. The three permitted relationship kinds are the ones lived reality has already demanded of listed shares (dual listings, DRs and their underlyings, renames and conversions that end one identity in another); *derivative-of* is not permitted — an equity derives from nothing. None is mandatory: a share that is nobody's twin, wrapper, or successor is complete.

---

## Capability Projection

What an engine holding an equity instance can learn — the complete truth, nothing else crosses the boundary:

| Query | Answer |
|---|---|
| Unit | one share |
| Quantity | whole-share default; fractional/lot: instance facts; non-negative |
| Acquisition | venue-traded |
| Settlement | cycle-based (length: instance fact) |
| Valuation question | continuous quotation |
| Flows admissible | dividend |
| Event families | split, merger, spin-off, rename, suspension, delisting |
| Existence | open-ended; may relate: same-entity, wraps, successor-of |

---

## Validation

- **No engine change required.** Every declaration is behavior the engines already exhibit for the platform's held stocks — lot validation, T+2 pendency, dividend admission, split interpretation, delisted-but-held positions. M8 converts the engines' implicit equity assumptions into declared, queryable facts; no engine learns anything new.
- **Constitutional vocabulary only.** Every declaration is a value on one of the seven axes; no new word, no new family, no new flow type was introduced.
- **No metadata.** No expense ratios, no free float, no company facts — nothing an engine doesn't branch on appears.
- **No classification.** No market, sector, currency, exchange, or wrapper name occurs anywhere above; Thai and US listings, common and preferred, DR and underlying are all this one kind, distinguished where distinction belongs.
- **No implementation logic.** No rounding, no price mathematics, no corporate-action arithmetic; the definition grants families and flows — their one owning implementation each lives in the engines.

## Related Documents

- [asset_definitions.md](../architecture/asset_definitions.md) — the constitution these declarations are written under
- [asset_definition_library.md](asset_definition_library.md) — the library charter and authoring guide
- [asset_definition_cash.md](asset_definition_cash.md) — the sibling definition; together they span the axes' extremes
- [ASSET_REGISTRY.md](../architecture/ASSET_REGISTRY.md) — the listing as the unit of identity; lifecycle statuses; relationships
