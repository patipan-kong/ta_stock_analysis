# Asset Definition: Cash

_A canonical Asset Definition of the platform library. Governed by [asset_definitions.md](../architecture/asset_definitions.md); authored per [asset_definition_library.md](asset_definition_library.md). Declarations only — no schemas, no code, no metadata, no classification._

| | |
|---|---|
| **Definition** | Cash |
| **Version** | v1 |
| **Status** | Canonical — shipped with the platform |
| **Individuation (D1)** | No other definition declares this contract |

---

## Purpose

Cash is the kind that denominates every other kind. It is the numeraire of the accounting core: every buy, sell, fee, tax, and income flow of every other asset has a cash counterleg, and NAV conservation is *measured* in it. Cash is therefore the one definition no portfolio can exist without — and, deliberately, the simplest text in the library: most of its axes declare honest absence, and the platform's laws require that absence to be as expressive as presence (D7).

One definition covers all currencies. A THB balance and a USD balance behave identically in every way an engine can ask about — *which* currency an instance is denominated in is an instance fact, never a definitional one (D10). "Thai cash" and "US cash" as separate definitions would fail the individuation law (D1): identical declarations, two names.

---

## Declarations

### Axis 1 — Unit Semantics

**Declared: the unit is one unit of the instance's currency; quantity is continuous to the currency's precision; quantity may not be negative; quantity is identical to native value.**

- *One currency unit.* Cash is counted in the money it is — there is no share, weight, or contract standing between the quantity and the amount.
- *Continuous, precision instance-refined.* Money subdivides; how far (two minor-unit decimals, zero, other) is a property of the instance's currency, refining this declaration within what it permits (D10).
- *Non-negative.* v1 models no credit: a cash balance below zero is not a smaller balance, it is a **borrowing** — a different economic fact that deserves its own kind (a liability) or an explicit future widening of this one, argued openly as a new version (§8.2 of the constitution). Until then, an operation that would drive cash negative is refused by the engine that owns conservation, and this declaration is what entitles it to refuse.
- *Quantity ≡ value.* The conservation peculiarity of the numeraire, declared rather than assumed: for cash, and only for cash, the number the ledger conserves and the number valuation reports are the same number. This declaration is what Axis 4's identity valuation stands on.

### Axis 2 — Acquisition Semantics

**Declared: not transactable — cash has no acquisition market. It moves only by transfer across the accounting boundary, and as the counterleg of other kinds' transactions.**

Challenged, because this is the counterintuitive declaration of the library. Three candidate mechanisms, each rejected:

- *Venue-traded?* No venue lists a currency balance for purchase in itself.
- *Bought and sold?* The platform never records a BUY of cash. A deposit is a **transfer** — a boundary-crossing flow, already first-class in the transaction vocabulary — and the cash that appears when a share is sold is **conservation**, not acquisition: the counterleg of another kind's disposal.
- *What about FX?* An FX conversion looks like "buying USD with THB." v1 is single-currency per portfolio, and FX is out of this version's scope by design. When multi-currency arrives (Phase 5), FX is an exchange **between two cash instances** — a transaction concept the universal vocabulary already reserves — not a change to this axis. If that judgment proves wrong, the correction is a new version of this definition, openly argued; it is recorded here so the future author knows the question was seen, not missed.

The declaration matters because of what it lets engines refuse: a BUY or SELL event naming a cash instance is *structurally inadmissible*, and the refusal is loud (D7). A statement import that tries to book one has misclassified a transfer, and the definition is what catches it.

### Axis 3 — Settlement Semantics

**Declared: instant.**

A cash movement is real the moment it is recorded; there is no pending state in which cash is committed but not settled. (The *other* leg of a trade may be pending under the traded kind's cycle — that pendency belongs to that kind's declaration, never to cash's.)

### Axis 4 — Valuation Semantics

**Declared: identity — an instance is worth its face amount in its own currency. No valuation question exists for Market Intelligence to answer.**

Challenged: *should cash be continuously valued?* No, and the reasons are constitutional, not practical:

- A continuous-quote declaration is a promise that Market Intelligence can be asked "what is this worth now?" and give an answer that could differ from the last one. For cash in its own currency the answer is the quantity, always, by Axis 1's quantity ≡ value. A valuation question whose answer is already in hand is not a question — declaring it would send an engine to observe a fact it possesses.
- The tempting counterexample — "my USD balance is worth more THB today" — is not a valuation of cash. It is the **portfolio's reporting-currency conversion** of a foreign balance: a question about the portfolio, answered with an FX observation Market Intelligence owns. The instance's native worth never moved. Putting that question on this axis would smuggle a portfolio concern into a kind's contract.
- Inflation — "cash loses value" — is a judgment-layer observation about purchasing power, not a valuation of the instrument. A definition that declared it would carry an opinion (D11).

### Axis 5 — Flow Grants

**Declared: INTEREST. Nothing else.**

- *Interest, granted.* Cash held in accounts earns interest in the real world; the flow is admissible whether or not any current balance happens to earn it. A grant is a statement that the flow is *meaningful for the kind* — not a prediction that it occurs (the same reading the universal model gives a non-paying stock's dividend support).
- *Dividend, coupon, rent, staking, distribution — all ungranted.* Each is income generated by holding something that *does* something; cash does nothing but be money. Any such flow arriving against a cash instance is a booking error, and the ledger's refusal (D7) is the detection.

### Axis 6 — Event-Family Grants

**Declared: none.**

Challenged: *should cash support corporate actions?* The serious candidate is **redenomination** — a state replacing its currency at a fixed ratio, structurally split-like, and historically real. It is not granted, deliberately:

- Grants are promises engines must honor; a speculative grant is an unpriced liability sitting in the treaty. The constitution's discipline is that the ladder is walked *by need, never speculatively* (constitution §9 — the same reasoning that deferred crypto's fork/airdrop families).
- No instance the platform can hold today faces a redenomination. The day one does, the widening is **additive** — a new version granting the applicable family — which is precisely the change versioning exists to make cheap (§8.2). Granting now buys nothing and asserts something untested.

### Axis 7 — Existence Pattern

**Declared: open-ended. No relationship participation — none permitted, none mandatory.**

Cash instances do not mature, expire, or convert; they persist as long as the currency does (and a currency's death is the redenomination question above, answered when real). No cash instance wraps, succeeds, or derives from anything in v1; multi-currency's arrival may argue a relationship between cash kinds and FX — argued then, not pre-granted now.

---

## Capability Projection

What an engine holding a cash instance can learn — the complete truth, nothing else crosses the boundary:

| Query | Answer |
|---|---|
| Unit | one currency unit; quantity ≡ native value |
| Quantity | continuous (precision: instance fact); non-negative |
| Acquisition | not transactable — transfer and counterleg only |
| Settlement | instant |
| Valuation question | none — identity; worth is face amount |
| Flows admissible | interest |
| Event families | none |
| Existence | open-ended; no relationships |

---

## Validation

- **No engine change required.** Every declaration above is behavior the accounting core already exhibits for cash: instant availability, no BUY/SELL, interest admissible, no valuation lookups. M8 transfers that truth from implicit code assumption to explicit declaration; nothing new is asked of any engine.
- **Constitutional vocabulary only.** Every declaration is a value on one of the seven axes (§5.1); no new word was introduced.
- **No metadata.** Account names, bank references, rate histories — none appear; none are definitional.
- **No classification.** No currency named, no jurisdiction, no market: *which* currency is an instance fact; where it is legal tender is classification's business.
- **No implementation logic.** No rounding rules, no formulas, no storage; the precision *authority* is declared (instance fact), never the arithmetic.

## Related Documents

- [asset_definitions.md](../architecture/asset_definitions.md) — the constitution these declarations are written under
- [asset_definition_library.md](asset_definition_library.md) — the library charter and authoring guide
- [asset_definition_equity.md](asset_definition_equity.md) — the sibling definition; together they span the axes' extremes
