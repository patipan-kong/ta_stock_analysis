# Market Data Platform

_The architecture of how information from the outside world becomes trusted canonical data inside the platform — without any engine ever learning where it came from._

_This is not an implementation document, not a provider comparison, and not an adapter design. It defines the layers, responsibilities, and trust boundaries between the external financial world and the platform's stable core. How individual providers are actually integrated — interfaces, adapters, configuration — is the subject of the forthcoming `PROVIDER_INTERFACE.md`; this document defines the platform those adapters will plug into._

_Read together with [PLATFORM_EVOLUTION.md](PLATFORM_EVOLUTION.md) (the layer stack this document occupies two layers of — Market Data Platform and External Integrations), [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md) (asset identity, the Asset Registry, and the capability model this document leans on constantly), and [../engineering/DECISION_LOG.md](../engineering/DECISION_LOG.md) (which already records real provider-quality incidents — settlement-price lag on Thai SET closes, depository-receipt symbol quirks — that this architecture generalizes from one-off fixes into structural answers)._

---

## 1. Philosophy

### Market Data ≠ Asset Identity

These are two different questions, and the whole architecture follows from refusing to let one system answer both:

- **Asset identity** answers *"what is this thing?"* — permanent, platform-owned, settled once by the Asset Registry, stable for decades. `asset_id` never changes because a vendor changed a suffix convention.
- **Market data** answers *"what is observable about this thing right now, or at some moment in the past?"* — prices, NAVs, dividends, calendars, FX rates. It is a stream of **observations**, sourced from outside, inherently perishable, inherently fallible, and always attributed to the moment and source of observation.

The failure mode of conflating them is concrete: if the thing that fetches prices also gets to decide what an asset *is*, then every provider outage is an identity crisis, every vendor symbol change silently re-keys history, and replacing a data source means re-litigating what the portfolio holds. UNIVERSAL_ASSET_ARCHITECTURE.md §3 already establishes the direction of authority — providers supply *evidence* for identity resolution; they never *define* identity. This document is the other half of that contract: the Market Data Platform supplies *observations about* assets the Registry has already identified. It is downstream of identity, never upstream.

### Why market data providers are replaceable

Because nothing about a price is provider-specific except its packaging. A closing price for a Thai bank stock is a fact about the world; the vendor that relayed it added a symbol convention, a field naming scheme, a timezone assumption, and a delivery delay — all packaging, all removable. If the platform strips the packaging at the boundary and stores only the canonical observation (which asset, what value, what moment, what currency, what provenance), then the provider's only lasting contribution is a provenance tag. Any other source that can observe the same fact is a drop-in substitute.

This is not hypothetical resilience theater. Providers change terms, degrade coverage, lag on specific markets (the decision log records exactly such a lag on SET closing auctions, worked around today by scheduling — a tactical fix this architecture turns into a structural one), or disappear. A platform whose core would notice any of that has coupled its multi-year accounting guarantees to another company's roadmap. PLATFORM_EVOLUTION.md §2 states the principle — *"losing any single provider must never be an architectural event"* — and this document is its enforcement mechanism.

### Why the Portfolio Engine must never know where data came from

Three reasons, in ascending order of severity:

1. **Determinism.** The Portfolio Engine's contract is: same ledger, same prices, same result, forever. "Same prices" is only meaningful if a price is a stored canonical fact, not a live answer from whoever responded fastest today. An engine that fetches is an engine whose output depends on network weather.
2. **Replayability.** Replaying 2026 in 2031 must use the prices as recorded, even if every provider that supplied them is gone. Provider knowledge inside the engine makes history hostage to vendor longevity.
3. **Correctness ownership.** If the engine knows sources, it inevitably grows source-specific compensations — "trust this vendor's currency field, adjust that one's timezone" — and data quality stops having a single owner. Quality is the Market Data Platform's job, done once, at the boundary, before data becomes canonical. Everything past the boundary trusts the data *because* the boundary exists.

The engine consumes canonical observations keyed by `asset_id`. Where they came from is recorded in provenance — available to auditors, invisible to arithmetic.

---

## 2. Responsibilities

### What the Market Data Platform owns

- **Discovery support** — answering "does the outside world know about an instrument matching this query?" during asset discovery (§4), as evidence handed to the Asset Registry.
- **Search** — user- and system-facing lookup across external universes ("find ADVANC", "find Thai ESG funds"), returned as candidate identities for the Registry to resolve.
- **Symbol resolution evidence** — mapping external strings (tickers, provider symbols, broker codes, ISINs) toward canonical `asset_id`s (§5). The Registry owns the final verdict; the Resolver here assembles the case.
- **Latest prices** — the most recent trustworthy valuation observation per asset, with explicit freshness.
- **Historical prices** — the time series of past observations, complete and calendar-aware, that replay and analytics depend on.
- **Fund NAV** — the NAV-cycle equivalent of pricing for mutual funds, RMF, SSF, and Thai ESG wrappers, treated as a first-class pricing mode, not a special case of OHLC.
- **Corporate action data** — external observations of splits, mergers, delistings, symbol changes: *detected and normalized here, adjudicated by the Asset Registry* (lifecycle is Registry territory per UNIVERSAL_ASSET_ARCHITECTURE.md §6; this platform is its sensory organ).
- **Benchmark data** — index and reference series consumed by the Benchmark Engine and AI Evaluation, held to the same normalization and validation standards as asset prices.
- **Market metadata** — externally observable descriptive facts (sector classifications, fund categories, exchange listings) delivered as candidate metadata for Registry stewardship.
- **Currency & FX** — exchange-rate observations, with the same freshness and provenance discipline as prices, because a mixed-currency portfolio is only as correct as its FX data.
- **Trading calendars** — which days and hours each market trades, holidays included: the data that tells the platform when an absent price is *expected* versus *missing* (§8).

### What belongs elsewhere

- **Asset identity and lifecycle verdicts** — Asset Registry (UNIVERSAL_ASSET_ARCHITECTURE.md §4, §6). This platform proposes; the Registry decides.
- **Transaction ingestion** — the Universal Input Layer (PLATFORM_EVOLUTION.md §5). A broker feed's *trade confirmations* are input events; the same broker's *price quotes* are market data. Same wire, two doors, never confused.
- **Accounting, replay, metrics** — the deterministic core, which consumes canonical data and never fetches.
- **Belief formation** — Decision Intelligence. Market data informs judgment; it never contains judgment.
- **Provider adapter design** — `PROVIDER_INTERFACE.md` (forthcoming).

---

## 3. Overall Architecture

```
External World
    every provider, feed, exchange, broker, document — chaotic, inconsistent, unowned
        ↓
Discovery Layer
    where the platform first learns an instrument might exist (§4)
        ↓
Resolver
    external strings and identifiers → candidate canonical identity (§5)
        ↓
Provider Router
    which source answers this request, by capability, market, quality, freshness (§6)
        ↓
Normalization
    provider dialects → one canonical observation model (§7)
        ↓
Validation
    is this observation trustworthy enough to become platform truth? (§8)
        ↓
Asset Registry
    identity confirmed; observations attached to permanent asset_ids
        ↓
Portfolio Engine
    consumes canonical, validated, provenance-tagged data — nothing else
```

Each layer exists to answer exactly one question, and the ordering is the argument:

- **Discovery before Resolution** — you cannot resolve what you have not encountered. Discovery produces *claims* ("something called ADVANC seems to exist on SET"); it asserts nothing.
- **Resolution before Routing** — you cannot route a request for data about an asset until you know *which* asset. Routing on raw symbols would push ambiguity downstream, where it becomes silent corruption instead of a visible resolution question.
- **Routing before Normalization** — the Router picks the source; only then is there a provider dialect to normalize. Routing decisions never leak past this point: everything downstream of Normalization is provider-blind.
- **Normalization before Validation** — validation rules are written once, against the canonical model. Validating provider-shaped data would mean one rulebook per vendor, which is how quality stops being a platform property.
- **Validation before the Registry** — nothing becomes attached to a permanent `asset_id` without passing quality gates. The Registry stores settled facts, not hopeful ones.
- **The Registry before the Engine** — the Portfolio Engine's one dependency for "what is this and what is it worth" is the Registry and the canonical data keyed to it. The engine sits at the end of the pipeline precisely so that it never has to know the pipeline exists.

The trust gradient runs top to bottom: data enters as *claim*, becomes *candidate*, becomes *canonical observation*, becomes *platform truth*. No shortcut across that gradient exists, for any asset class, ever.

---

## 4. Discovery Layer

Discovery is the moment the platform first encounters an instrument it does not yet track. It has exactly one job: convert an encounter into a **discovery claim** — "here is evidence that something exists, and here is everything I observed about it" — and hand that claim to the Resolver and Registry. Discovery never mints an `asset_id`; it never writes anything permanent.

### The discovery doors

- **User Search** — a person types "ADVANC" or "Thai ESG fund". The platform searches external universes and returns candidates; choosing one triggers resolution and, possibly, Registry creation.
- **CSV Import** — a statement or export mentions instruments the platform has never seen. Each unfamiliar row is a discovery claim carrying whatever identifiers the file happened to include.
- **Broker Import** — a brokerage feed lists holdings, some unknown. Broker codes are often the *weakest* identifiers (proprietary, undocumented, reused), which is exactly why they arrive as claims, not facts.
- **API Import** — any programmatic source introducing instruments as a side effect of its actual payload.
- **Manual Entry** — the user describes an asset no provider knows: a property, a private holding, physical gold in a vault. Discovery with *zero external evidence* is valid — it proves the layer is about encountering assets, not querying vendors.

### Why discovery is provider-independent

Because the same real-world instrument can be discovered through any door, in any order, and must converge on the same single `asset_id`. A fund discovered via CSV on Monday and via broker feed on Thursday is one asset, not two — which is only achievable if discovery produces source-neutral claims that one Resolver and one Registry adjudicate centrally. The moment a discovery door is allowed to "just create" assets in its own source's vocabulary, the platform has as many identity systems as it has doors, and reconciliation becomes an archaeology project. Manual Entry is the proof case: an asset class with no provider at all (property, private equity) flows through the identical claim → resolve → register pipeline, because the pipeline was never about providers in the first place.

---

## 5. Symbol Resolution

The Resolver answers one question: **given an external string and its context, which single `asset_id` is meant?** It is the sole component allowed to reason about the messy many-to-many world of external naming, and its output is always either one `asset_id`, a ranked set of candidates for confirmation, or an honest "unknown."

### The evidence hierarchy

Not all identifiers are equal, and the Resolver weighs them accordingly:

1. **ISIN** — the strongest single claim: globally scoped, issuance-assigned. Still not absolute (one ISIN can trade on several exchanges in several currencies), so ISIN resolves *the security*, and exchange/currency context resolves *the listing*.
2. **CUSIP / SEDOL** — strong within their registries (North America; UK/Ireland), absent elsewhere. Regional strength, not global truth.
3. **Ticker + Exchange + Market** — a ticker alone is weak (recycled, collided, reused across markets); a ticker *anchored to an exchange and market* is usually decisive.
4. **Provider symbols** — a vendor's private spelling (suffix conventions, DR encodings — the platform's own decision log documents the depository-receipt case). Meaningful only inside that provider's universe; the Resolver treats them as coordinates in a foreign system, translated on arrival and never stored as identity.
5. **Broker symbols** — weakest of all: proprietary, undocumented, occasionally recycled. Resolvable only through accumulated, confirmed mappings.
6. **Currency** — rarely identifying on its own, frequently the tiebreaker between listings of the same security.

The **canonical symbol** sits outside this hierarchy entirely: it is an *output* of resolution — the platform's own stable name, assigned at Registry creation — never an input clue. External evidence flows in; canonical identity flows out; the arrow never reverses.

### The worked ambiguities

- **AAPL** — looks unambiguous, isn't: the US listing, several depository-receipt wrappers on other exchanges (including a Thai DR), and provider-specific spellings of both. Ticker alone cannot distinguish an asset from a wrapper *around* that asset; market context or an explicit user choice must. The Resolver's job is to know these are *related but distinct* `asset_id`s and never silently substitute one for the other.
- **ADVANC** — one company, multiple external spellings across providers (bare ticker on the home exchange, suffixed forms in vendor universes). Classic many-strings-one-asset: every spelling maps to the same `asset_id`, and no engine ever learns more than one name for it.
- **BABA** — one economic entity, genuinely different listings (US ADR, Hong Kong shares) with different currencies, calendars, and settlement. Classic one-name-many-assets: the same four letters must resolve to *different* `asset_id`s depending on market context, and when context is absent the Resolver must ask, not guess.
- **VOO** — an ETF whose ticker collides with nothing today but whose identity spans an ISIN, exchange listing, and a fund structure with NAV alongside market price. Resolution must land on one `asset_id` that carries both pricing capabilities, not two half-assets.
- **BTC** — no ISIN, no exchange in the traditional sense, no issuer, and dozens of venue-specific pair symbols (against USD, THB, stablecoins). Resolution here is convention-based: the platform defines the canonical asset, and every venue symbol is a mapping *to* it. Crypto is the proof that the Resolver's model cannot assume the traditional identifier stack exists at all.

### The resolution contract

When evidence is decisive, resolve silently. When it is ambiguous, **surface the ambiguity** — a ranked candidate list, a user confirmation, a quarantined claim — and record the confirmed mapping so the same question is never asked twice. What the Resolver may never do is guess silently: a wrong price is a bad day, but a wrong *identity* poisons the ledger, and the ledger is forever. Resolution confidence follows the same principle the Universal Input Layer applies to transactions (PLATFORM_EVOLUTION.md §5): uncertain input is flagged as uncertain until confirmed, and the human owns the final word on their own financial truth.

---

## 6. Provider Router

Once a request is expressed canonically — "daily closing prices for `asset_id` X over range R" — something must decide which external source answers it. That is the Router: the one component that knows more than one provider exists.

### The routing dimensions

- **Capability Routing** — the foundation. A request requires a capability (§9); only providers declaring that capability are candidates. A source with no fund-NAV capability is never asked about a Thai ESG fund, not because code says `if provider == ...` but because the capability table says nothing.
- **Market Routing** — capability within a market. A provider may be excellent for US equities and useless for SET, definitive for crypto and silent on bonds. Routing is per (capability × market), because coverage always is.
- **Primary / Fallback** — for each (capability × market), an ordered preference: the source trusted first, and the sources tried when it fails. Fallback answers carry their true provenance and quality tier — a fallback price is better than no price, but the platform never pretends it was a primary answer.
- **Quality Routing** — preference informed by observed quality (§10), not vendor reputation. A provider that repeatedly ships settlement-lagged closes for a given market loses primary status *for that market*, structurally — turning the decision log's scheduled-workaround pattern into an architectural behavior.
- **Freshness Routing** — the required recency shapes the route. An intraday signal check and a decade of backfill are different requests even for the same asset; the source best for one is often wrong for the other.

### What the Router is not

It is not a load balancer (this is about trust, not throughput), not a cost optimizer first (correctness outranks economy, per the platform's root principle), and not a merger of answers — when multiple sources disagree, that is a *validation* finding (§8), not something the Router papers over by averaging. The Router selects; it never edits.

The Router's decisions are recorded in provenance and end at the Normalization boundary. Downstream, nobody knows routing happened — which is precisely what makes re-routing, provider replacement, and provider retirement invisible non-events for the core.

---

## 7. Data Normalization

Every provider speaks its own dialect: different field names, different timezone conventions, different adjusted-versus-unadjusted price defaults, different dividend date semantics (declared? ex? paid?), different notions of what a "close" even is on a half-trading day. None of this variety carries information the platform wants — it is packaging (§1), and Normalization is where packaging is removed, once, at the boundary.

### One canonical model per observation kind

The platform defines a single internal shape for each kind of external fact — defined by the platform's own semantics, never as a superset of provider fields:

- **Price** — one valuation observation: which `asset_id`, what value(s), which moment, which currency, what kind of price (traded close, auction settlement, mid, appraisal), and provenance. The *kind* matters: the decision log's SET settlement-lag incident was, at root, two different price-kinds being conflated.
- **Dividend** — one income event with its full date semantics (declaration, ex-date, payment) made explicit, because providers routinely report only one date and imply the others.
- **Corporate Action** — one structural event (split, merger, symbol change, delisting) in a vocabulary aligned with the Registry's lifecycle model (UNIVERSAL_ASSET_ARCHITECTURE.md §6), so that what Normalization produces, the Registry can directly adjudicate.
- **FX** — one currency-pair observation at one moment, with the same provenance discipline as prices — because in a multi-currency portfolio, FX *is* pricing.
- **Benchmark** — one index observation, normalized identically to asset prices so the Benchmark Engine and AI Evaluation never handle vendor-shaped series.
- **Fund NAV** — one NAV-cycle valuation, first-class and distinct from OHLC: it has a cutoff time, not a trading session, and pretending it is a "daily close" breaks both validation and replay semantics for every fund wrapper the platform supports.
- **Trading Calendar** — one market's schedule as canonical data: sessions, holidays, half-days. Calendars are normalized observations too — providers disagree about holidays more often than anyone expects.

### Boundary Normalization

The principle (PLATFORM_EVOLUTION.md §2: *normalize at the boundary, never in the core*) has a precise meaning here: **the canonical model is the only vocabulary that exists downstream of this layer.** No provider field name, unit convention, timezone assumption, or symbol spelling survives past Normalization. Validation validates canonical observations. The Registry stores canonical observations. Engines consume canonical observations. When a provider changes its format, exactly one place in the platform notices — and when a new provider arrives, teaching the platform its dialect is the *whole* integration, because everything downstream was built never to care.

---

## 8. Validation Layer

Normalization makes data speak the platform's language; Validation decides whether to believe it. This is the last gate before an observation becomes canonical truth attached to a permanent `asset_id` — and it is where the platform's data quality is *made*, not merely measured.

### The validation responsibilities

- **Missing data** — a gap where an observation should exist. The trading calendar makes this decidable: no price on a SET holiday is *expected absence*; no price on a Tuesday session is a *defect*. Without calendar-awareness, these are indistinguishable, which is why calendars are a first-class responsibility (§2).
- **Duplicate data** — the same observation arriving twice (two providers, one provider twice, a fallback overlapping a primary). Deduplication happens here, with provenance — never downstream as a compensating heuristic in metrics or replay (ADR-002's prohibition, extended from ledger to market data).
- **Invalid currency** — an observation whose currency contradicts the asset's native currency in the Registry. Almost always a resolution or provider defect; caught here, before it silently mis-values a position by a factor of an exchange rate.
- **Stale price** — an observation that is technically present but too old for its declared purpose. Staleness is explicit and per-use: a week-old appraisal is excellent data for a property and disqualifying for a crypto asset — the asset's capability profile (UNIVERSAL_ASSET_ARCHITECTURE.md §5) defines what fresh *means*.
- **Missing trading day** — a hole inside a historical series, distinct from staleness at the tip; replay and analytics need series whose gaps are all *explained* gaps.
- **Corporate action lag** — a price series that shifted (split, large dividend) before the corresponding corporate action arrived. Validation's job is to *detect the incoherence and quarantine*, not to guess the adjustment — adjudication belongs to the Registry's lifecycle process.
- **Timezone** — the quiet killer. Every observation's moment is normalized to an unambiguous instant at the boundary; "daily close" only has meaning relative to a specific market's clock, and a platform spanning Bangkok, New York, and Hong Kong sessions cannot leave this implicit anywhere.
- **Outliers** — a value wildly inconsistent with its own series or its market's day. Flagged and quarantined, never silently dropped and never silently accepted: an outlier is either a data defect or the most important observation of the year, and only scrutiny — sometimes human — can tell which.

### The quality stance

Three commitments define the layer. **Validation is calendar- and capability-aware** — correctness is judged against what *this* asset in *this* market should look like, which is how one rulebook serves stocks, NAV funds, gold, and property without special-casing. **Failures are loud** (PLATFORM_EVOLUTION.md invariant 9) — quarantined data is visible, counted, and attributable; a silent gap is a lie about coverage. And **suspect data never advances** — the deterministic core's right to trust its inputs unconditionally is purchased here, at the boundary, every day. Quality over availability: a missing price is an honest, visible, recoverable state; a wrong price accepted into canon is a defect that replay will faithfully reproduce forever.

---

## 9. Capability Model

Providers differ in what they can do at all — one has deep historical equity data but no fund NAVs, another has crypto and FX but no corporate actions, an exchange feed has definitive settlement prices for one market and nothing else. The anti-pattern is encoding this as provider-specific branches; the architecture instead declares **capabilities** — the same move UNIVERSAL_ASSET_ARCHITECTURE.md §5 makes for assets, applied to sources.

### The capability vocabulary

Each provider declares which of these it supports, per market where relevant:

- **Search** — can look up instruments by name or symbol fragment.
- **Price** — can supply a current/latest valuation.
- **History** — can supply daily-resolution historical series.
- **Intraday** — can supply finer-than-daily observations.
- **Corporate Actions** — can report splits, mergers, symbol changes, delistings.
- **Benchmark** — can supply index/reference series.
- **Metadata** — can supply descriptive facts (sector, classification, listing details).
- **Fund NAV** — can supply NAV-cycle valuations for fund structures.
- **Financial Statements** — can supply fundamentals.
- **ETF Holdings** — can supply fund composition.
- **Options Chain** — can supply derivatives data (the same forward-looking capability UNIVERSAL_ASSET_ARCHITECTURE.md §11 anticipates on the asset side).

### Why routing depends on capabilities

Because it makes the Router's logic *generic and closed* while the provider universe stays *open*. The Router's only question is "who declares the capability this request needs, in this market, at what quality?" — a question whose code never changes when a provider is added, dropped, or re-scoped. Contrast the alternative: provider-named branches scattered through routing logic, each addition a code change, each removal a risky cleanup, each special case a small hole in the provider-independence guarantee.

The model also creates a two-sided match that keeps requests honest end to end: an *asset's* capabilities (it supports NAV, not OHLC) determine what kind of data may be requested for it; a *provider's* capabilities determine who can answer. A request for intraday prices on a mutual fund fails at request formation — the asset doesn't support it — before any provider is consulted. Both sides of the conversation are described, not hardcoded, and a future capability (real-time streams, ESG scores — §13) extends the vocabulary once rather than rewriting the middle.

---

## 10. Provider Quality

Quality is not a reputation a vendor claims; it is a track record the platform observes, per provider, per capability, per market. Six dimensions matter, and they are deliberately independent — a source can excel at five and fail the sixth:

- **Freshness** — how quickly an observation reflects reality. The platform's own history proves freshness is market-specific: the decision log records a provider whose Thai closing prices lagged final settlement by minutes — perfectly fresh for US equities, materially stale for SET auctions. Freshness is measured where it bites.
- **Reliability** — does the source answer when asked? Uptime, error rates, rate-limit behavior. Unreliability is survivable with fallbacks; *unpredictable* unreliability is what fallback ordering exists to absorb.
- **Coverage** — which assets, markets, and history depths exist at all. Coverage gaps are honest and routable-around; the danger is coverage that *appears* present but is thin (sparse fund NAVs, patchy Thai ESG data).
- **Latency** — how fast answers arrive. Usually the least important dimension for this platform — a portfolio accounting system needs *right* far more than it needs *fast* — but it shapes routing for interactive search versus overnight backfill.
- **Completeness** — are answers whole? Series without silent holes, dividends with all their dates, corporate actions that arrive at all. Incompleteness is more dangerous than absence because it masquerades as success; §8's calendar-aware validation exists largely to unmask it.
- **Consistency** — does the source agree with itself over time? Stable conventions, non-shifting history, adjustments announced rather than snuck in. A provider that silently rewrites its own past is uniquely corrosive to a platform whose core promise is reproducible replay — detected by re-validation, punished by quality routing.

Two consequences follow. **Quality feeds routing** (§6): observed degradation demotes a source for the affected capability × market, structurally and reversibly, with no code change. And **quality is provenance-visible**: because every canonical observation records its source, quality analysis is always retrospectively possible — the platform can ask "how good was our gold pricing in 2027, and from whom?" years later. What quality assessment never does is edit data: a low-quality observation is quarantined or demoted, never "corrected" by the platform pretending to know better than its sources. The platform's honesty about what it observed is itself an invariant.

---

## 11. Error Handling

The outside world fails constantly; the design question is what the platform does when it does. One rule governs every case: **degrade loudly, degrade honestly, and never let a boundary failure become a core corruption.** A failure at the edge is an operational event; the same failure silently absorbed becomes a data defect that replay reproduces forever.

- **Provider unavailable** — the Router walks the fallback order (§6). If a fallback answers, the observation is canonical but provenance-marked as fallback-sourced. If no source answers, the request fails *visibly* — a recorded gap with a reason, never a stale value masquerading as current.
- **Price unavailable** — an asset no reachable source can currently value. The platform serves the last canonical observation *explicitly labeled with its age*, and every consumer sees the staleness: the UI shows it, analytics carry it, and Decision Intelligence knows its inputs are degraded. What never happens is a fabricated, interpolated, or quietly-stale price presented as fresh — for some asset classes (property, private equity) "the last appraisal, honestly dated" is not even degradation, it is the normal and correct state, which is why honesty-about-age is the architecture rather than an error path.
- **Symbol not found** — resolution failure. The claim is quarantined with its evidence, surfaced for confirmation, and *nothing is created*: no speculative asset, no guessed mapping. An unresolvable symbol in an import is a visible exception the user completes — because a mis-resolved identity is the one error the platform can never fully repair downstream (§5).
- **Benchmark missing** — analytics that compare against the benchmark degrade explicitly: metrics that need it are marked uncomputable for the gap rather than computed against a substitute series nobody chose. AI Evaluation inherits the gap honestly — a grade computed against a missing benchmark is not a grade.
- **Corporate action delayed** — the dangerous asymmetry: the price series shifts before the explaining event arrives. Validation detects the incoherence (§8), quarantines the affected span, and holds it out of canon until the Registry adjudicates the action. Better a visible two-day hole than a phantom −50% return the AI Evaluation engine dutifully grades someone on.
- **Resolver conflict** — evidence points to two identities, or providers disagree about what a symbol is. Never auto-picked. The conflict is surfaced with its evidence, the human (or an explicitly delegated policy) decides, and the confirmed mapping is recorded so the conflict never recurs. Identity is the one domain where the platform prefers *stopping* to *guessing*.

The common shape: every failure mode has a *defined degraded state* that is observable, attributable, and recoverable — and the deterministic core never participates in any of it. The Portfolio Engine does not retry, does not fall back, does not interpolate; it consumes canonical data and reports honestly when data is absent. Failure handling lives at the boundary because that is where failure happens.

---

## 12. Caching Strategy

Caching here is not a performance afterthought; it is part of the trust architecture. The governing insight: **most market data is immutable once settled.** A 2024 closing price will never change (absent a corporate action, which is itself an event, not an edit) — so historical canonical data is less a "cache" than a permanent record, while the volatile edge (latest prices, search results) is genuinely cache-like. The strategy follows the data's own nature:

- **Search Cache** — short-lived convenience over external search results. Least trusted, most disposable; never a source of identity (resolution always goes through the Resolver and Registry, cached or not).
- **Metadata Cache** — descriptive facts change slowly and unpredictably; cached generously, refreshed deliberately, always subordinate to the Registry's stewarded record — the cache accelerates reads of Registry truth, it never *is* the truth.
- **Price Cache (latest)** — the volatile tip. Its freshness policy is per asset-capability: minutes matter for crypto, the NAV cycle defines "current" for funds, a quarter is fresh for an appraised property. One cache concept, per-asset-class freshness semantics — the capability model (§9) doing its job again.
- **Historical Cache** — settled observations, kept effectively forever. This is the store that makes replay provider-independent: once a series is canonical, no future provider outage, retirement, or history-rewrite can touch what the platform already recorded. Backfilled once, validated once, trusted permanently.
- **FX Cache** — mirrors the price pattern: volatile tip, immutable history. FX history is as replay-critical as price history for any multi-currency portfolio and is kept to the identical standard.
- **Benchmark Cache** — settled index history, permanent like historical prices, because AI Evaluation's grades and the Benchmark Engine's comparisons must be as reproducible as the returns they judge.

**Ownership** is the architectural point: every cache is owned by the Market Data Platform, below the canonical boundary. No engine caches provider data privately — a private cache inside an engine is a second source of truth with an undocumented refresh policy, which is exactly the duplication ADR-004 exists to forbid. Engines read canonical data; the Market Data Platform decides, in one place, how canonical data is kept warm, kept fresh, and kept forever. Invalidation is event-driven where it matters most: a corporate action adjudicated by the Registry invalidates affected derived series *by that event*, not by TTL luck. And the existing per-kind TTL discipline in today's implementation (technical/news/fundamental caches with distinct lifetimes, per ARCHITECTURE.md) is the embryo of this design — what changes is not the instinct but the ownership: one platform layer, one policy, no private copies.

---

## 13. Future Extensions

The test of this architecture is what a new source of world-knowledge costs. The answer, by design, is: a new door and possibly a new capability word — never a core change.

- **Realtime Streaming** — a push-based source is a provider with an *Intraday/streaming* capability and an inverted delivery direction. Observations still arrive as claims, still normalize, still validate, still land as canonical data with provenance. The Portfolio Engine notices nothing; Decision Intelligence simply finds fresher observations when it reads.
- **Broker APIs** — one connection, two doors, cleanly split: trade confirmations enter through the Universal Input Layer as proposed ledger events; quotes and holdings-metadata enter here as market data. The split (§2) is what keeps a broker outage from ever being an accounting question.
- **Official Exchange APIs** — the structural fix the decision log's SET settlement-lag entry always wanted: a direct exchange feed is just a provider with superior *Freshness* and *Consistency* for its home market, and quality routing (§6, §10) promotes it to primary for that market — a configuration event, not an architecture event.
- **Alternative Data** — flows, positioning, on-chain metrics: new observation kinds with honest confidence labels, normalized at the boundary, consumed as *evidence for beliefs* by Decision Intelligence. Never a bypass into the deterministic layers (PLATFORM_EVOLUTION.md §8 already stakes this out).
- **Economic Indicators** — rates, inflation, GDP: observations about *markets* rather than assets — the regime detector's future diet. They extend the canonical model with market-scoped observation kinds; they touch nothing downstream of belief formation.
- **News** — already present in embryonic per-stock form; generalizes into event-shaped observations (what happened, to which `asset_id`s, with what claimed mechanism) keyed by resolved identity — the Resolver working on prose instead of symbols. Strictly belief-layer input, graded like every other signal by AI Evaluation.
- **ESG** — scores and classifications as metadata-kind observations with named methodologies and provenance — which matters doubly here, because ESG "facts" are really vendor opinions, and provenance is what keeps the platform honest about that. Thai ESG fund *eligibility* remains Registry metadata; ESG *scoring* flows through here.
- **Satellite Data** — the deliberately exotic case that proves the shape: parking-lot counts and shipping traffic are just low-trust, high-latency observations with unusual provenance. If the architecture can treat satellite imagery as "one more provider with one more capability answering with one more observation kind," it can absorb sources nobody has invented yet.

The pattern is identical every time: new door (provider + capability declaration), possibly new vocabulary (observation kind), same hallway (resolve → route → normalize → validate), same destination (canonical data keyed by `asset_id`). The Portfolio Engine's code is untouched in every scenario above — which is not a happy accident but the acceptance criterion each extension must meet.

---

## 14. Principles

1. **Market data is replaceable; asset identity is permanent.** Providers supply perishable observations about assets whose identity the platform alone owns. No vendor event — outage, retirement, format change, symbol change — may ever alter what an asset *is*.
2. **The platform stores observations, not opinions about vendors.** Every canonical fact is source-neutral in shape and provenance-tagged in origin: usable without knowing its source, auditable without losing it.
3. **Normalize at the boundary — the canonical model is the only vocabulary downstream.** No provider field name, symbol convention, timezone assumption, or format quirk survives past Normalization. One place notices when a vendor changes; that is the whole point of having the place.
4. **Business logic never depends on provider formats — or provider existence.** Engines are written against canonical observations keyed by `asset_id`. A provider's name appears in provenance and routing tables, nowhere else.
5. **Quality over availability.** A visible gap is honest and recoverable; a wrong or silently stale value accepted into canon is a defect replay will reproduce forever. When the choice is "answer badly or fail loudly," fail loudly.
6. **Capability over provider.** Routing asks "who can do this, for this market, at what observed quality" — never "call vendor X." Providers are rows in a capability table, and the table's code never changes when the rows do.
7. **Identity resolves before data flows.** No observation attaches to a symbol; observations attach to resolved `asset_id`s, and ambiguity halts for confirmation rather than guessing. A wrong price is a bad day; a wrong identity is a poisoned ledger.
8. **Settled history is immutable and provider-independent.** Once validated into canon, historical observations are the platform's permanent property. Replay in 2031 uses 2026's data as recorded, whoever originally supplied it and whether they still exist.
9. **Failures degrade loudly and end at the boundary.** Every error mode has a defined, observable, attributable degraded state. The deterministic core never retries, never falls back, never interpolates — it consumes canonical data and reports honestly when data is absent.
10. **The Portfolio Engine consumes only canonical data.** It never fetches, never resolves, never routes, never caches privately, and cannot name a single provider. The entire Market Data Platform exists so that sentence stays true while the outside world churns.

---

## Related Documents

- [PLATFORM_EVOLUTION.md](PLATFORM_EVOLUTION.md) — the platform-wide philosophy and layer stack this document details two layers of
- [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md) — asset identity, the Asset Registry, and the capability model this platform serves and mirrors
- [ARCHITECTURE.md](ARCHITECTURE.md) — today's implementation, whose symbol normalization and per-kind caching are the embryonic forms this design generalizes
- [../engineering/DECISION_LOG.md](../engineering/DECISION_LOG.md) — the recorded provider-quality incidents (settlement-price lag, DR symbol handling) this architecture answers structurally
- `PROVIDER_INTERFACE.md` _(forthcoming)_ — the provider adapter contract: how individual sources actually plug into the Router, Normalization, and capability declarations defined here
