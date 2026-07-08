# Universal Asset Architecture

_The domain model for what an Asset **is**, so that Portfolio Engine, Replay Engine, Accounting Engine, Analytics Engine, and AI Evaluation Engine never have to change to support a new one._

_This is not an implementation document. It designs the canonical Asset model, identity strategy, registry responsibilities, capability model, lifecycle, validation boundary, and transaction vocabulary — not database tables, provider adapters, or JSON configuration. Provider integration is the subject of the forthcoming `MARKET_DATA_PLATFORM.md`; this document defines what that platform will ultimately feed._

_Read together with [PLATFORM_EVOLUTION.md](PLATFORM_EVOLUTION.md) (§4 Universal Asset Vision, §6 Platform Boundaries, §9 invariants — this document is that vision made specific), [ARCHITECTURE.md](ARCHITECTURE.md) (today's equity-only implementation, which this architecture generalizes without invalidating), and [OPTIMIZER_PHILOSOPHY.md](OPTIMIZER_PHILOSOPHY.md) (the judgment/arithmetic boundary this document extends to asset identity)._

---

## 1. Philosophy

### Why the Portfolio Engine must never know Yahoo, Polygon, Morningstar, or a broker API

The Portfolio Engine's entire value is that it is deterministic: same ledger, same prices, same rules, same result — replayable years later, on any machine, forever. That guarantee has a hidden precondition that is easy to violate without noticing: **the engine's inputs must mean the same thing regardless of where they came from.**

The moment the engine contains a branch like "if this symbol came from Yahoo, adjust the suffix; if it came from a broker feed, trust the currency field; if it's a `.BK` symbol, look up the sector map" — determinism is no longer a property of the engine. It is a property of the engine *plus whatever provider happened to answer that day*. Swap providers, and replay can silently diverge. Extend to a new market, and the branch count grows. This is exactly the failure PLATFORM_EVOLUTION.md §2 names: *"if the core needs an `if broker == ...`, the boundary has failed."*

There is a second, sharper reason. Providers do not agree on identity. Yahoo Finance's `ADVANC.BK` and a Thai broker's internal code and a data vendor's ISIN-keyed record may all describe the same equity — or may not, depending on corporate actions, delisting, or plain vendor inconsistency. If the Portfolio Engine transacts in provider symbols, it has implicitly outsourced "what is this asset?" — a question with real financial consequences — to whichever provider happened to answer last. An engine that owns accounting cannot afford to have its notion of identity be somebody else's implementation detail.

### Why every asset becomes a canonical internal Asset

The answer is the same discipline the platform already applies to money: a `Transaction` row is not "whatever the broker's statement said," it is the platform's own canonical record, informed by but independent of its source. An **Asset** must be the same kind of object — the platform's own settled answer to "what is this thing?", built once, referenced everywhere, and stable even when every provider that helped build it changes, disagrees, or disappears.

Concretely: the Portfolio Engine, Replay Engine, Accounting Engine, Analytics Engine, and AI Evaluation Engine should each be able to do their job having been handed nothing but an `asset_id` and a quantity — no symbol, no exchange string, no provider name, no market-specific logic. Everything that would tempt an engine to special-case a market or a provider belongs one layer down, resolved once by the Asset Registry (§4) before the engine ever sees it.

This is not abstraction for its own sake. It is the same argument PLATFORM_EVOLUTION.md makes for inputs generally, applied to identity specifically: **normalize at the boundary, so the core never has to.**

---

## 2. Universal Asset Model

An Asset is the platform's canonical answer to "what is this thing, and what can be done with it?" — independent of any provider's opinion, current at the moment it's read, and stable across the asset's entire lifecycle.

### Universal fields — true of every asset, regardless of class

These describe identity and tradability, and every engine may rely on them existing and meaning the same thing for a Thai bank stock, a gold gram, and an asset class invented five years from now.

- **`asset_id`** — the platform's own permanent, opaque identifier. Never reused, never repurposed, never derived from a symbol. This is the only handle the Portfolio Engine, Replay Engine, and Accounting Engine ever hold.
- **`asset_type`** — the broad kind of thing this is (equity, fund, precious metal, digital asset, fixed income, cash, real property, …). Coarse enough to be stable; see §5 for the finer-grained behavioral distinctions, which are capabilities, not types.
- **`market`** — the regulatory/economic market the asset primarily belongs to (e.g., Thailand, United States, Hong Kong), independent of exchange or currency. Relevant for holidays, disclosure regimes, and tax treatment.
- **`exchange`** — where it trades, if it trades on one. Optional — gold and property have no exchange; that absence is meaningful, not missing data.
- **`currency`** — the currency the asset is natively priced and settled in. Universal even for assets priced by weight or appraisal, which still resolve to a currency of record.
- **`canonical_symbol`** — the platform's own stable symbol, chosen once, changed never (see §3). Not any provider's symbol.
- **`display_symbol`** — what the user sees, which may follow local convention or user preference and may legitimately differ from the canonical symbol.
- **`identifiers`** — the bundle of external identity references this asset is known by (ISIN, CUSIP, SEDOL, broker codes, provider symbols — see §3). Structurally a collection, not a single field, because an asset accumulates identifiers over its life and should never be forced to pick just one.
- **`tradable`** — whether the platform currently permits new transactions against this asset. Distinct from lifecycle status (§6); an asset can be non-tradable while still valid to hold (e.g., suspended, delisted-but-held).
- **`fractional_support`** — whether quantities may be non-integer. True for most funds and crypto; false for many equities; the deciding factor for how the Accounting Engine rounds and validates quantities.
- **`lot_size`** — the minimum tradable/transactable increment, where the market defines one. Absent where it doesn't apply.
- **`settlement_cycle`** — how long after a transaction the asset/cash actually moves (T+0, T+2, T+3, instant, or not applicable). The Accounting Engine needs this to reason about pending vs. settled state; it does not need to know *why* a given market's cycle is what it is.

### What belongs in `metadata`, and why

Everything else — anything true of *some* assets but not asset-hood generally — lives in an open, asset-type-specific `metadata` bundle: a fund's expense ratio and NAV-calculation time, a bond's coupon rate and maturity date, a property's address and appraisal cadence, a stock's sector and free-float, a crypto asset's chain and consensus mechanism, tax-advantaged wrapper details (RMF holding-period rules, SSF eligibility windows, Thai ESG qualifying criteria).

The test for "universal field vs. metadata" is not "how important is this fact" — a bond's coupon rate matters enormously to whoever holds the bond. The test is **"does the Portfolio Engine, Replay Engine, or Accounting Engine need to branch on this to do its job?"** If no engine needs to read it to replay a ledger or conserve NAV, it is metadata: informative to Analytics, AI Evaluation, and Presentation, invisible to the accounting core. This is what keeps the universal model universal — it must stay small enough that a wholly new asset class can be described without ever needing to widen it.

---

## 3. Asset Identity

### The problem identity actually has to solve

A single real-world asset accumulates multiple names over its life: an ISIN assigned at issuance, a CUSIP for US clearing, a SEDOL for UK/LSE reference, whatever code a specific broker uses internally, whatever symbol a specific data provider prefers (already a live example: Yahoo Finance's `.BK` suffix and its separate Depository-Receipt suffix convention, both documented in ARCHITECTURE.md as vendor-specific quirks the platform already normalizes around). None of these is wrong; they simply serve different audiences, and none of them was designed with the others in mind. They can drift out of sync, be reassigned, or simply not exist for some assets (property has no ISIN; a private fund may have no CUSIP).

Identity architecture exists to answer one question without ambiguity: **given any of these strings, which single `asset_id` does it mean, right now?**

### The identity stack

- **`asset_id`** (internal, canonical) — the only identity that business logic is allowed to hold onto. Stable for the asset's entire life in the platform, regardless of what happens to any external identifier.
- **`canonical_symbol`** (internal, canonical) — the platform's own human-readable symbol, assigned once at asset creation and never reassigned, even if the asset is later renamed on its home exchange (see §6 Rename). It exists so a person or a log line can reference an asset without needing the opaque `asset_id`, without reintroducing provider-symbol ambiguity.
- **External identifiers** (ISIN, CUSIP, SEDOL, broker-specific codes, per-provider symbols such as a Yahoo or vendor symbol) — all recorded, none authoritative, all just *evidence used to resolve to an `asset_id`* at the moment an external system hands the platform a string.
- **`display_symbol`** (presentation-only) — cosmetic. Two users, or one user in two contexts, may legitimately see different display symbols for the same `asset_id`.

### Why business logic must use `asset_id`, never a provider symbol

Three failure modes fall out immediately once any engine holds a symbol string instead of an `asset_id`:

1. **Symbols get reassigned; identity should not.** Exchanges recycle tickers after delisting. If the Portfolio Engine keys a holding by symbol, a recycled ticker silently merges two unrelated companies' histories.
2. **The same asset has different symbols in different places.** A DR and its underlying, or a cross-listed stock, is one economic exposure with several provider spellings. Symbol-keyed logic either double-counts it or needs a special case per market — precisely the branching §1 forbids.
3. **Symbols are provider opinions, and providers disagree or vanish.** An `asset_id` is a platform fact. A symbol is somebody else's naming choice, made for their own purposes, subject to change without the platform's consent.

The resolution direction is therefore always one-way and always at the boundary: **external identifier → Asset Registry lookup → `asset_id` → everything downstream.** No engine reverses that arrow.

---

## 4. Asset Registry

The Asset Registry is the single subsystem that is allowed to know that providers, symbols, and external identifiers exist at all. Every other subsystem — Portfolio Engine, Replay Engine, Accounting Engine, Analytics Engine, AI Evaluation Engine, Presentation — depends on the Registry instead of depending on any provider, and receives only canonical `asset_id`s and Asset records in return.

### Responsibilities

- **Discovery** — the process by which a new asset (a stock not yet held, a new fund, a first-time crypto purchase) becomes known to the platform at all, whether initiated by user action, an import, or a data feed encountering something new.
- **Canonicalization** — the resolution described in §3: given an external identifier or symbol from any source, determine the one `asset_id` it refers to, creating a new Asset only when discovery (above) genuinely warrants it, never as a side effect of an ambiguous lookup.
- **Validation** — confirming an asset record is well-formed and internally consistent (§7 covers the transaction-time validation surface specifically; the Registry is where an asset's own static correctness is guaranteed).
- **Status** — tracking where an asset currently sits in its lifecycle (§6): active, suspended, delisted, merged-away, and so on — the fact every other engine needs before deciding whether an action against this asset makes sense today.
- **Metadata stewardship** — owning the asset-type-specific `metadata` bundle (§2): what shape it takes per `asset_type`, and that it stays coherent as new asset types are introduced.
- **Provider mappings** — the record of which external identifiers and provider symbols resolve to which `asset_id`, including historical mappings that no longer apply (a delisted ticker still needs to resolve correctly for historical replay).

### Why every other subsystem depends on the Registry instead of on providers

This is the architectural inversion the whole document rests on. Today, "does this symbol exist, what does it trade as, what currency is it in" are questions various parts of the platform answer by asking a data provider directly, sometimes with market-specific logic sitting alongside the question (the DR-symbol normalization and Thai sector map in today's `ARCHITECTURE.md` are the concrete, present-day instances of this pattern). The Registry's job is to become the *only* place that pattern is allowed to exist.

Concretely: the Portfolio Engine asks the Registry "is `asset_id=X` tradable, fractional, what lot size" — never a provider. The Analytics Engine asks the Registry for an asset's `market` and `metadata.sector` for attribution — never a provider. The AI Evaluation Engine grades a recommendation against an `asset_id` — never a symbol string that might mean something different next year. Every engine's contract becomes "I depend on the Registry's answer," which is one dependency, versioned and owned in one place, instead of N engines each depending on M providers.

This mirrors, at the identity layer, exactly what PLATFORM_EVOLUTION.md §2 already established for prices ("no engine may know where a price came from") and for business rules (ADR-004, one implementation, all consumers) — applied here to the question of *what an asset is* rather than *what an asset is worth* or *how a number is computed*.

---

## 5. Asset Capabilities

### Why capability, not type, is the right axis

`asset_type` (§2) answers "what broad kind of thing is this" and is deliberately coarse and stable. But engines don't actually need to branch on type — they need to know **what this specific asset can do**: does it have daily closing prices, does it pay something, can it be corporate-actioned, can it be fractionally held. Branching on type (`if asset_type == "crypto": ...`) reintroduces exactly the special-casing this document exists to eliminate, and it scales badly: every new asset type would require finding and updating every such branch across every engine.

A **capability model** replaces "what type is this" with "what can this do," expressed as a set of independent, queryable properties an Asset either has or doesn't:

- **Supports OHLC** — has open/high/low/close price data (most exchange-traded instruments; not gold-by-weight, not property).
- **Supports NAV** — is priced by periodic net-asset-value calculation rather than continuous trading (mutual funds, RMF, SSF, Thai ESG funds).
- **Supports Dividends** — can generate a dividend cash flow.
- **Supports Coupons** — can generate periodic fixed-income interest.
- **Supports Corporate Actions** — can undergo splits, mergers, spin-offs, symbol changes (§6).
- **Supports Staking Rewards** — can generate a crypto-native yield event.
- **Supports Rental Income** — can generate periodic income from physical holding (property).
- **Supports Fractional Trading** — overlaps with, but is conceptually distinct from, `fractional_support` in §2: this is about whether *trading* mechanics allow fractional order sizes, which some markets restrict even when the underlying quantity concept is continuous.
- **Supports Short Selling** — can be held at negative quantity under the platform's accounting rules.
- **Supports Options** — has a derivable derivatives market (relevant when the platform eventually reasons about instruments *on* an asset, not just the asset itself).
- **Supports Daily Pricing** — has at least once-a-day valuation (nearly universal; the exception is illiquid property between appraisals).
- **Supports Intraday Pricing** — has valuation finer than daily (exchange-traded instruments; not funds priced once daily by NAV, not property).

### Why this is architecture, not a feature list

Every engine that currently would need an `if asset_type in (...)` branch instead asks the Registry "does this `asset_id` support X?" and behaves generically off the answer. The Replay Engine doesn't need to know what a bond is to replay a coupon payment — it needs to know this asset **Supports Coupons**, and therefore a `COUPON` transaction against it is expected and meaningful. The Accounting Engine doesn't special-case gold — it asks whether the asset **Supports Fractional Trading** to decide how to validate a quantity.

This is also what makes §11's extension claim literally true rather than aspirational: a wholly new asset class (options, private equity, a future asset type not yet imagined) is introducible by declaring which capabilities it has. If every capability it needs already exists, no engine changes at all. If it needs a genuinely new capability, that capability is added once, to the shared vocabulary, and every engine that already knows how to ask "does this asset support X" gains the ability to handle it — which is a very different, and far cheaper, kind of change than teaching five engines about one new asset type each.

Capability over inheritance also avoids a subtler trap: a class hierarchy (`Equity extends TradableAsset extends Asset`) forces every asset into exactly one lineage and makes multi-behavior assets (a fund that also pays dividends and also has NAV; a REIT-like property vehicle that has both rental income and OHLC pricing) awkward or impossible to express cleanly. A flat set of independent capabilities has no such ceiling.

---

## 6. Asset Lifecycle

An Asset's identity (§2–3) is permanent; its **status** moves through a lifecycle that every engine can consult without needing to understand *why* a status changed.

- **Create** — a new `asset_id` is minted, either from user action (adding a never-before-seen holding) or Registry discovery (§4) encountering an asset for the first time. Creation is cheap and asset-type-agnostic; it does not require every metadata field to be known yet.
- **Import** — an asset already known outside the platform (an existing brokerage holding, a legacy portfolio) is brought in. Import resolves external identifiers to an `asset_id` via canonicalization (§3–4) before anything is recorded against it — it never invents a second `asset_id` for something the Registry can already resolve.
- **Activate** — the asset becomes tradable (`tradable=true`); transactions against it are now permitted.
- **Suspend** — trading is temporarily disallowed (regulatory halt, market suspension) while the asset remains held and valid; existing holdings are unaffected, new transactions are not.
- **Delist** — the asset is no longer tradable on its home venue, permanently. It remains a valid, permanent `asset_id` for as long as any ledger references it — delisting changes what can happen *going forward*, never what already happened.
- **Merge** — two `asset_id`s resolve, from a point in time forward, to a single ongoing identity (e.g., an acquisition). The pre-merge `asset_id`s are never deleted or reassigned; a merge is recorded as a relationship between them, and history that predates the merge continues to reference the original `asset_id`.
- **Rename** — an asset's `canonical_symbol` or `display_symbol` may need to change to track a real-world rename, but `asset_id` never does. A rename is a new fact recorded against the same permanent identity, not a new asset.
- **Replace** — an asset is superseded by a successor (e.g., a share-class conversion), recorded as an explicit relationship between two `asset_id`s, in the same spirit as Merge.
- **Corporate Action** (splits, spin-offs, special dividends, and the like) — a lifecycle event that changes quantity, cost basis, or spawns a new related asset, but is itself just a category of event the Registry and Asset model must be able to represent generically across asset types, not an equity-specific concept bolted onto the model.

### Why the Replay Engine is unaffected by any of this

Every lifecycle transition above is expressed as **data attached to a permanent `asset_id`**, never as a structural change to that identity and never as a rewrite of history. The Replay Engine's contract has always been "replay the ledger of events, in order, against the state they describe" (per PLATFORM_EVOLUTION.md §9's immutability invariant) — and every lifecycle event here is exactly that: one more event in the timeline, dated, attached to an `asset_id` that never changes shape. A delisted asset replays identically before and after delisting, because delisting doesn't touch the ledger — it touches `tradable`. A merged asset's pre-merge history replays exactly as recorded, because the merge is a forward-looking relationship, not a retroactive identity change. The Replay Engine never needs a special case for "this asset went through a corporate action" because it was never taught to reason about *why* an event happened — only to apply events in order. Lifecycle is metadata about an asset's present and future; the ledger is a record of its past, and the two never have to agree with each other's shape.

---

## 7. Asset Validation

Validation answers, at the moment a transaction is attempted, whether it is legitimate — and it must do so without ever asking a provider, because a provider being unreachable must never be able to corrupt or block the accounting core's judgment about what is structurally valid.

### Responsibilities

- **Asset exists** — the referenced `asset_id` resolves to a real, known Asset in the Registry.
- **Tradable** — the asset's current lifecycle status (§6) permits new transactions.
- **Market open** — the relevant market/exchange calendar (owned by the eventual Market Data Platform, consulted here, not reimplemented here) allows a transaction to be dated as occurring now.
- **Currency** — the transaction's currency is consistent with the asset's native currency, or is an explicit, recorded FX conversion (§9).
- **Settlement** — the transaction's implied settlement is consistent with the asset's `settlement_cycle`.
- **Lot size** — the transacted quantity respects the asset's `lot_size`, where one applies.
- **Fractional rules** — the transacted quantity respects `fractional_support` / Supports Fractional Trading.
- **Required identifiers** — the asset carries whatever external identifiers its `asset_type` and jurisdiction require for the transaction to be legitimate (e.g., a tax-advantaged Thai fund category needing its qualifying metadata present).

### Why this layer must be provider-independent

Validation is a gate the Accounting Engine passes every transaction through before it becomes permanent, immutable history (PLATFORM_EVOLUTION.md invariant 2). If that gate's answer depended on a live provider call, two unacceptable things follow: a provider outage becomes an accounting outage (violating the platform's deterministic-core guarantee), and replaying history later could re-validate differently than it did the first time, because the provider's live answer today differs from what it would have said back then. Validation therefore consults only the Registry's own recorded state (Asset record, capabilities, lifecycle status) — data the platform itself owns and that is exactly as available, and exactly as it was, whenever replay asks the same question again.

---

## 8. Portfolio Engine Boundary

### What the Portfolio Engine must never receive

It must never receive `ADVANC.BK`, never `AAPL`, never any provider symbol, exchange-suffixed string, or broker code — because every one of those is an external opinion about identity (§3), and the Portfolio Engine's determinism guarantee depends on never being handed an input whose meaning could shift under a provider's decisions.

### What it receives instead

A **canonical asset representation**: an `asset_id`, resolved once at the boundary by the Asset Registry, accompanied only by the universal fields (§2) and capability flags (§5) the engine's arithmetic actually needs — never the identifiers, never the metadata, never anything that required asking a provider a question. Concretely, the shape of what crosses this boundary is closer to *"asset_id=X, quantity=Q, currency=native, fractional=yes"* than to *"ADVANC.BK, 100 shares."*

This is the same boundary discipline PLATFORM_EVOLUTION.md §5 establishes for transaction inputs generally — "many doors, one hallway," where the hallway carries only canonical events — applied specifically to *what an asset is* rather than *what happened to it*. The Universal Input Layer normalizes the *event*; the Asset Registry normalizes the *thing the event happened to*. Both normalizations complete before the Portfolio Engine is invoked, and the engine is architecturally incapable of distinguishing a Thai stock from a US stock from gold except by asking the Registry-supplied capability flags it was handed — which is exactly the point.

---

## 9. Universal Transaction Model

This section identifies which transaction *concepts* are universal across every present and future asset class — not the record shape, not field types, not storage. The question is: what kinds of things happen to an asset, in a vocabulary broad enough to cover a Thai bank stock and a rental property without special-casing either?

- **BUY / SELL** — acquisition and disposal, universal to every asset that can be owned in variable quantity, whether the "market" is an exchange, a fund's NAV window, a bullion dealer, or a private sale of property.
- **DIVIDEND** — a cash distribution tied to equity-like ownership; the concept generalizes to fund distributions even where the label differs.
- **INTEREST** — a cash flow tied to lending or cash-like holding — relevant to bonds, cash accounts, and potentially crypto lending, under one concept rather than one per asset class.
- **RENT** — periodic income tied to physical-property holding; structurally the same shape as DIVIDEND and INTEREST (periodic income against a held asset) even though the asset class is entirely different.
- **STAKING** — a crypto-native yield event; again structurally a periodic-income concept, distinguished from DIVIDEND/INTEREST/RENT only by which asset class it attaches to and what generated it.
- **TRANSFER** — movement of an asset in or out of the platform's tracked custody without a BUY/SELL economic event (an in-kind transfer between accounts, a wallet move) — needed universally the moment more than one custody location exists for the same asset.
- **FEE** — a cost incurred in connection with another transaction or with holding the asset, universal across every asset class, already decomposed today (per DECISION_LOG.md's Fee Decomposition entry) into components that generalize cleanly.
- **TAX** — a withholding or levy tied to a transaction or a holding period, conceptually distinct from FEE (already true today), and universal in the same way.
- **FX** — a currency conversion event, universal the moment any asset's native currency differs from the portfolio's reporting currency — which is already true for cross-border holdings and becomes structurally central once multiple markets are held simultaneously.

The unifying observation: every one of these is either **a change in quantity held** (BUY, SELL, TRANSFER), **a cash flow generated by holding** (DIVIDEND, INTEREST, RENT, STAKING), or **a cost/adjustment layered on either** (FEE, TAX, FX). That three-way grouping — not the asset class the event happens to attach to — is the axis the universal transaction vocabulary should be organized around, so that a wholly new income concept for a future asset class (something not yet on this list) has an obvious existing bucket to generalize into rather than demanding a fourth grouping.

No transaction concept above is asset-type-specific in the sense that would require the Accounting Engine to know what a bond or a crypto wallet is — each is asset-type-specific only in *which* assets it applies to, a fact the capability model (§5) already expresses (an asset Supports Coupons, or doesn't; the transaction concept itself, INTEREST, is universal either way).

---

## 10. Capability Matrix

Illustrative, not exhaustive — the point is the shape of variation, not a final enumeration. A ✓ means the capability is generally true for typical assets of that class; real individual assets may vary (a non-dividend-paying US stock still has Dividends *support*, i.e., the mechanism exists, even in a period it isn't exercised).

| | Thai Stocks | US Stocks | ETF | Mutual Fund | Gold | Crypto | Property | Bond | Cash |
|---|---|---|---|---|---|---|---|---|---|
| **Pricing (OHLC)** | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | ✓ | — |
| **NAV-based Pricing** | — | — | partial | ✓ | — | — | — | — | — |
| **Income (Dividend/Coupon/Interest/Rent/Staking)** | Dividend | Dividend | Dividend | Distribution | — | Staking (some) | Rent | Coupon | Interest |
| **Corporate Actions** | ✓ | ✓ | ✓ | rare | — | fork/airdrop | — | call/maturity | — |
| **FX Relevance** | when cross-border | when cross-border | when cross-border | when cross-border | ✓ (often USD-priced) | ✓ | rare | when cross-border | ✓ |
| **Intraday Pricing** | ✓ | ✓ | ✓ | — | ✓ | ✓ (continuous) | — | limited | — |
| **Settlement Cycle** | T+2 | T+2 | T+2 | T+1/T+2 (NAV cutoff) | varies | near-instant | manual/legal | T+1/T+2 | instant |
| **Tax Treatment Variance** | standard | standard | standard | RMF/SSF/ESG wrappers vary | capital gains | varies by jurisdiction | significant (transfer/holding taxes) | coupon withholding | minimal |
| **Fractional Support** | — (lot-based) | broker-dependent | broker-dependent | ✓ | ✓ (by weight) | ✓ | — | — | ✓ |

The matrix exists to demonstrate that variation is real and significant — and entirely expressible as capability differences (§5) and metadata differences (§2), never as a reason to fork the Portfolio Engine, Replay Engine, or Accounting Engine per row.

---

## 11. Extension Strategy

The claim this whole document exists to make good on: adding a new asset class is an act of **description** — declaring identity, capabilities, and metadata shape — never an act of **surgery** on the engines. Four illustrative cases:

**Japanese Stocks.** A new `market` value, a new exchange, a new currency, a settlement cycle already within the range the model expresses, and identifiers (a Japanese security code alongside whatever ISIN exists). No new capability is required — Japanese equities support OHLC, dividends, and corporate actions exactly like existing equities. This is pure Asset Registry data entry: new `market`/`exchange`/`currency` values and provider mappings, zero engine changes.

**Singapore Stocks.** Structurally identical to the Japanese case — a new market/exchange/currency combination riding on capabilities the model already has. If Singapore's settlement cycle or lot-size convention differs from what's already modeled, it is data on the Asset record, not new engine logic, because `settlement_cycle` and `lot_size` were already designed as per-asset fields (§2), not per-market-hardcoded constants.

**Options.** The first genuinely new capability: an options contract has an underlying `asset_id`, a strike, an expiry, and exercise semantics that today's capability list doesn't cover. This is handled by extending the capability vocabulary (§5) — Supports Options as an attribute of the underlying, plus recognizing "derivative-on-an-asset" as a new relationship the Asset Registry can express — argued and added openly, exactly as §16 of OPTIMIZER_PHILOSOPHY.md requires for genuinely new pipeline stages. The Portfolio Engine still only ever sees `asset_id` + quantity + the relevant capability flags; it does not need to understand options mechanics to hold a position correctly, only to know this asset settles differently and may derive value from another `asset_id`.

**Commodities (beyond gold).** Silver, oil, agricultural commodities: same shape as gold — Supports Daily Pricing, priced by weight/unit rather than share count, no dividend-like income, FX-relevant. Zero new capabilities needed; this is a new `asset_type` value with metadata (unit of measure, storage/delivery considerations) and Registry entries, nothing more.

**Private Equity.** The hardest case, and instructive precisely because it's hard: illiquid, appraisal-priced rather than market-priced, often with no daily or even monthly valuation, potentially no `lot_size` or standard settlement concept at all. This is handled by the same mechanism as property (§4 of PLATFORM_EVOLUTION.md already names property as a stretch case): capabilities that are mostly *absent* (no OHLC, no intraday, no standard settlement) rather than present, appraisal-driven valuation events recorded the same way any other pricing event is recorded, and ownership/transaction events (BUY, SELL, TRANSFER) that work identically to every other asset class because §9's transaction vocabulary was never actually equity-specific. No engine change; the honesty is in acknowledging some fields simply won't apply, which the model already accommodates by design (§2's "absence is meaningful, not missing data").

In every case, the test from PLATFORM_EVOLUTION.md §4 holds: if a new asset class requires editing the Portfolio Engine, Replay Engine, or Accounting Engine, the abstraction has failed and the abstraction is what gets fixed — not the engine, and not by adding a special case, but by finding the genuinely missing capability or field and adding it once, to the shared vocabulary every asset draws from.

---

## 12. Principles

1. **The Asset Registry is the single source of truth for what an asset is.** Every other subsystem asks the Registry; none maintains its own opinion.
2. **Portfolio Engine owns accounting; it does not own identity.** It receives resolved `asset_id`s and capability flags, never symbols, never provider data.
3. **Market Data never owns asset identity.** Providers supply prices and evidence for identity resolution; they never get to define what an asset *is* — that is the Registry's canonicalization, not any single provider's symbol convention.
4. **Business logic never depends on provider symbols.** Every engine, every rule, every calculation references `asset_id`. A symbol is a display concern or a resolution input, never a key.
5. **Capability over inheritance.** What an asset can do is a set of independent, queryable flags, not a rigid type hierarchy — because real assets have overlapping, not mutually exclusive, behaviors.
6. **Normalize identity at the boundary, exactly as inputs are normalized at the boundary.** The Asset Registry is to "what is this thing" what the Universal Input Layer (PLATFORM_EVOLUTION.md §5) is to "what happened" — both complete their work before anything reaches the deterministic core.
7. **`asset_id` is permanent; every other identifier is evidence.** Renames, relistings, and provider changes are facts recorded against a stable identity, never reasons to create a new one or mutate an old one.
8. **Absence is data.** A field or capability an asset lacks (no exchange, no lot size, no intraday pricing) is a meaningful, expected state — not a gap to paper over with a default.
9. **New asset classes are described, not engineered.** If describing one requires touching the Portfolio Engine, Replay Engine, or Accounting Engine, the universal model — not the new asset class — has found its limit, and the model is what gets extended.
10. **Lifecycle changes an asset's status, never its history.** Merges, renames, delistings, and corporate actions are forward-looking facts layered onto a permanent identity; replayed history is never rewritten to accommodate them.
11. **Validation is provider-independent and replay-stable.** A transaction's legitimacy is decided from the platform's own recorded state, so the answer is identical whenever it is asked — today, in a replay, or a decade from now.
12. **This document defines the domain model; it does not choose providers.** How prices, identifiers, and feeds actually arrive is the concern of the forthcoming Market Data Platform — this document exists so that platform has a stable, correct thing to feed data *into*.

---

## Related Documents

- [PLATFORM_EVOLUTION.md](PLATFORM_EVOLUTION.md) — the platform-wide philosophy and layer architecture this document specifies for assets
- [ARCHITECTURE.md](ARCHITECTURE.md) — today's implementation (equity-only symbol conventions, sector system) that this model generalizes
- [OPTIMIZER_PHILOSOPHY.md](OPTIMIZER_PHILOSOPHY.md) — the judgment/arithmetic boundary this document extends to asset identity
- [DECISION_LOG.md](DECISION_LOG.md) — the record of why (Fee Decomposition, DR Symbol Handling, and other precedents this model builds on)
- `MARKET_DATA_PLATFORM.md` _(forthcoming)_ — provider integration, adapters, and data-sourcing strategy built on top of this domain model
