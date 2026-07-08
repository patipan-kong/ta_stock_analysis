# Provider Interface

_The architectural contract between external data providers and the Market Data Platform: what every provider adapter owes the platform, and what the platform promises never to know about any provider._

_This is not an implementation guide, not API documentation, and not tied to any vendor. [MARKET_DATA_PLATFORM.md](MARKET_DATA_PLATFORM.md) defined the pipeline that turns outside information into canonical truth; this document defines the **socket** at the top of that pipeline — the one shape every external source must be adapted into before the platform will listen to it. Where the two documents touch the same concepts (capabilities, routing, quality, caching), that one describes the platform's side of the contract and this one describes the provider's side; per the platform's own single-source-of-truth rule, neither restates the other's half._

_Read together with [PLATFORM_EVOLUTION.md](PLATFORM_EVOLUTION.md) (the invariants), [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md) (asset identity — the thing no provider may ever own), [MARKET_DATA_PLATFORM.md](MARKET_DATA_PLATFORM.md) (the consuming platform), and [PORTFOLIO_DOMAIN_MODEL.md](PORTFOLIO_DOMAIN_MODEL.md) (the portfolios that ultimately depend on all of it without knowing any of it exists)._

---

## 1. Philosophy

### The position of the boundary

```
External World
    vendors, feeds, exchanges — their formats, their symbols, their moods
        ↓
Provider Adapter          ← the ONLY component that speaks a vendor's dialect
        ↓
Provider Interface        ← the contract: one shape, every adapter, no exceptions
        ↓
Market Data Platform      ← routing, validation, canonical storage
        ↓
Asset Registry            ← identity
        ↓
Portfolio Engine          ← deterministic accounting
        ↓
Analytics / AI Evaluation ← judgment over canonical truth
```

Everything below the Provider Interface consumes canonical models and nothing else. Everything above it is expected to be messy, vendor-specific, and frequently rewritten. The interface is the waterline: provider knowledge exists only above it, and it must never rise.

### Why providers are replaceable

Because the platform never asks a provider for anything only that provider could say. Every question the platform poses through this interface — what is this instrument called, what did it close at, when does its market trade — is a question about the *world*, which the vendor merely relays. The vendor's genuine contributions are packaging (formats, symbols, conventions) and logistics (delivery, latency, coverage), and the adapter's entire purpose is to strip the first and absorb the second, leaving only the world-fact plus a provenance tag. A provider that contributes only packaging and logistics is, by construction, substitutable by any other source that can observe the same facts.

The platform's own history is the proof this matters: a documented settlement-price lag on one market's closes, a vendor-specific depository-receipt symbol convention that had to be normalized at every call site — each a small tax paid because provider knowledge had leaked past where an interface should have stopped it. This document exists so those taxes are paid exactly once, in one layer, by design.

### Why business logic must never depend on provider APIs

Three layers of the argument, each stricter than the last:

1. **Change isolation.** Vendor APIs change on vendor schedules. If business logic touches them, every vendor change is a platform change; behind an interface, it is one adapter's maintenance.
2. **Determinism.** The Portfolio Engine's contract — same ledger, same prices, same result, forever — is only honest if a "price" is a canonical stored fact, not a shape defined by whoever served it. A provider concept inside business logic makes the meaning of recorded history contingent on a vendor's documentation.
3. **Meaning.** Provider APIs encode provider *opinions*: what a symbol denotes, which timezone is implied, whether history arrives adjusted. Business logic that consumes those opinions raw has delegated semantics — what its own numbers mean — to an outside party with no duty to the platform's invariants. Canonical models exist precisely so that meaning is decided once, by the platform, at the boundary.

The four engines named in this document's goal — Portfolio, Replay, Analytics, AI Evaluation — sit so far below the waterline that they cannot name a single provider, and the architecture's acceptance test is that this remains true no matter how many providers exist.

---

## 2. Responsibilities

### What a Provider (through its adapter) is responsible for

A provider is a **witness**: it reports what it can observe about the external world, in the platform's language, with honest labels. The observable duties:

- **Search** — report which instruments in the provider's universe match a query, as *candidate evidence* for discovery — never as settled identity.
- **Metadata** — report externally observable descriptive facts (classifications, listing details, fund categories) as candidates for Asset Registry stewardship.
- **Latest Price** — report the most recent valuation the provider can see, labeled with its moment, currency, and kind (traded close, auction settlement, mid, NAV — the price-kind vocabulary of MARKET_DATA_PLATFORM.md §7).
- **Historical Price** — report past valuation series over a requested range, with explicit statements about adjustment convention and any gaps the provider knows about.
- **FX** — report currency-pair observations with the same moment-and-provenance discipline as prices.
- **Benchmark** — report index and reference series, held to the identical standards as asset prices.
- **Fund NAV** — report NAV-cycle valuations as their own pricing mode, never disguised as daily closes.
- **Corporate Actions** — report structural events (splits, mergers, symbol changes, delistings) the provider has observed, as *claims for Registry adjudication* — the sensory-organ role, never the judge.
- **Trading Calendar** — report market sessions, holidays, and half-days for the venues the provider covers.

Cross-cutting all nine: every answer carries **provenance** (who observed this, when, via which capability) and **honesty about limits** (what the provider was asked but could not answer, stated as absence — never papered over).

### What a Provider must never do

- **Never assert identity.** A provider maps queries to *its own* symbols and supplies identifiers as evidence; the Asset Registry alone decides what an `asset_id` is (UNIVERSAL_ASSET_ARCHITECTURE.md §4). An adapter that creates, merges, or renames platform assets has crossed the one line that can poison the ledger.
- **Never write past the boundary.** No adapter touches the Registry, the ledger, snapshots, or any canonical store directly. Adapters *return* observations; the Market Data Platform decides what becomes canon (validation is downstream of the adapter, deliberately — §4).
- **Never fill gaps creatively.** No interpolation, no stitching another source's data into its own answers, no "probably the same as yesterday." A gap is reported as a gap; inventing data at the adapter level would defeat the validation layer by feeding it plausible fabrications.
- **Never carry business meaning.** No adapter knows what a portfolio is, what a benchmark is *for*, or why anyone wants a price. The moment an adapter branches on platform intent, business logic has leaked upstream across the waterline — the mirror image of the leak §1 forbids downstream.
- **Never fail silently.** Partial answers, rate limits, and unreachable upstreams are reported as what they are, with reasons — the platform-wide loud-degradation invariant (PLATFORM_EVOLUTION.md invariant 9) applies at this boundary first, because this is where most failures originate.

---

## 3. Provider Contract

The conceptual interface — the set of questions the platform may ask any provider, phrased as architectural responsibilities. Every adapter answers this same set (or declares, via capabilities, which subset it can answer); no adapter offers extra doors.

- **Search Assets** — *"What instruments in your universe match this text?"* Returns candidates with whatever identifiers the provider knows (its symbols, ISINs where available, names, venues) — raw material for the Resolver, never resolved identity.
- **Resolve Symbol** — *"What do you know about this specific external identifier?"* Returns the provider's own description of what that string denotes in *its* universe. This is evidence-gathering for the platform's Resolver (MARKET_DATA_PLATFORM.md §5); the answer contributes to resolution and never concludes it.
- **Get Latest Price** — *"What is the most recent valuation you can observe for the instrument you know by this reference?"* Answered with value, moment, currency, price-kind, and the provider's own freshness claim.
- **Get Historical Prices** — *"What valuations did you observe over this range?"* Answered with a series plus explicit adjustment convention and known-gap declarations, so the validation layer judges a complete confession rather than a tidy fiction.
- **Get Corporate Actions** — *"What structural events have you observed for this instrument in this range?"* Answered as dated event claims in the provider's best detail, understanding the Registry will adjudicate.
- **Get Benchmarks** — *"What reference series can you supply, and what are their observations over this range?"* Same shape and standards as historical prices.
- **Get Exchange Calendar** — *"When does this market trade?"* Sessions, holidays, half-days — answered as calendar claims that the platform normalizes into its canonical calendars.

Three properties of the contract matter more than its member list. **It is closed** — a new kind of question (news, economic series, statements) is added to the contract and the capability vocabulary once, platform-wide, never as one adapter's private extension. **It is uniform** — the platform asks every provider the same question the same way; adapters absorb the translation, which is what makes the Router able to substitute one source for another mid-flight. **It is stateless in meaning** — every answer is a self-contained observation (what, when, whence); no answer's meaning depends on a previous answer, a session, or adapter memory, because canonical storage — not adapters — is where the platform keeps state.

---

## 4. Canonical Models

Every provider returns a different shape: different field names, different timezone assumptions, adjusted or unadjusted history by different defaults, different dividend-date semantics, different opinions about what a "close" is on a half-day. None of that variety survives the adapter.

The rule of this section is a single sentence with sharp consequences: **nothing crosses the Provider Interface except canonical platform models.** The canonical vocabulary itself — Price, Dividend, Corporate Action, FX, Benchmark, Fund NAV, Trading Calendar — is defined once, by the platform, in MARKET_DATA_PLATFORM.md §7; this document adds the boundary-side obligations:

- **Normalization happens inside the adapter, before the boundary — always.** There is no "raw mode," no debugging passthrough, no temporary exception where vendor-shaped data crosses for convenience. A single leaked vendor field becomes a dependency the moment anything reads it, and dependencies on accidents are how boundaries rot.
- **Translation, not interpretation.** The adapter converts representation (field names, units, timezones, symbol spellings) and must not convert *meaning*: it does not decide an outlier is an error, does not smooth a gap, does not reclassify an ambiguous event. Judgment about trustworthiness belongs to the validation layer, which judges all providers by one rulebook — a rulebook that only works because everything reaching it is already one shape.
- **Fidelity plus confession.** The canonical model carries what the provider actually said, plus explicit markers for what it could not say (unknown adjustment convention, missing date semantics, unlabeled price-kind). An adapter that quietly defaults an unknown into a plausible value has laundered uncertainty into false confidence — the exact failure provenance and confidence labels exist to prevent.
- **The dialect dies at the boundary.** Downstream of the adapter, no component can tell which vendor supplied an observation except by reading its provenance tag. That indistinguishability is the measurable definition of this whole document: if any consumer behaves differently based on *which* provider answered — other than through recorded quality and provenance — the interface has failed.

This is Boundary Normalization (PLATFORM_EVOLUTION.md §2) at its sharpest point: teaching the platform a new vendor's dialect is writing one adapter, and it is also the *entire* integration.

---

## 5. Capability Model

Not every provider can answer every contract question, and the architecture's response is the platform's now-standard move — the third application of the same pattern, after assets (UNIVERSAL_ASSET_ARCHITECTURE.md §5) and the platform-side capability table (MARKET_DATA_PLATFORM.md §9): **declare, don't branch.**

### The declaration

Every adapter declares, per market where relevant, which capabilities its provider genuinely supports:

- **Asset Search** — can match queries against an instrument universe.
- **Price History** — can supply daily-resolution series.
- **Realtime** — can supply live or near-live observations (pull or push).
- **Fund NAV** — can supply NAV-cycle valuations.
- **Corporate Actions** — can report structural events.
- **FX** — can supply currency-pair observations.
- **Financial Statements** — can supply fundamentals.
- **ETF Holdings** — can supply fund composition.
- **News** — can supply event-shaped observations about assets.
- **Economic Data** — can supply market-scoped series (rates, inflation, indicators).

The declaration is a **truthfulness obligation**, not a marketing surface. Declaring a capability means answering that contract question with real data at usable quality in the declared markets; a capability a provider technically has but serves badly (sparse fund NAVs, token corporate-action coverage) is better left undeclared and discovered later than declared and silently hollow — observed quality (§7) will eventually expose the difference, but honest declarations keep the routing table meaningful from day one.

### Why routing depends on capabilities, not provider names

Because names couple and capabilities don't. A router that asks "who declares Fund NAV for Thai funds, at what observed quality?" has logic that never changes as providers come, go, improve, or decay — the answer changes, the question doesn't. A router that asks "is this the vendor we use for Thai funds?" has hardcoded an answer, and every provider event becomes a code event. Names also rot silently: a vendor that quietly drops a data family leaves name-based routing *believing* in coverage that no longer exists, while capability-based routing fails over the moment the declaration is corrected. The deeper point is symmetry: assets declare what can be done *to* them, providers declare what they can *do*, and the platform's middle is generic machinery matching the two — the entire provider universe reduced to rows in a table whose consuming code is closed.

---

## 6. Provider Routing

Routing is platform machinery, specified in MARKET_DATA_PLATFORM.md §6 — the Router owns primary/fallback ordering, capability routing, market routing, quality routing, and freshness routing. This section states only what the routing concepts *demand of the provider side of the contract*, so the two halves mesh:

- **Primary Provider** — being primary is a routing status, not an adapter property. No adapter knows it is primary, behaves differently because it is, or assumes it will remain so. Primacy is assigned per capability × market by the platform and revoked without the adapter's cooperation.
- **Fallback Provider** — fallback answers are ordinary answers: same contract, same canonical models, same provenance discipline. The *platform* records that a fallback served the request; the adapter neither knows nor cares that another source failed first. This is what makes failover instantaneous — there is no "fallback mode" to enter.
- **Capability Routing** — the routing table is built from the declarations of §5, which is why declaration truthfulness is a contract obligation rather than a courtesy: the Router can only be as honest as the declarations beneath it.
- **Regional Routing** — a provider excellent for one market and useless for another declares per-market capabilities, and routing composes coverage across providers per (capability × market). No adapter is ever asked to be good everywhere; the platform's coverage is the *union* of honest partial declarations — which is also why regional specialists (a home-market exchange feed, a local fund-data source) integrate as first-class citizens rather than special cases.
- **Quality Routing** — observed quality (§7) re-ranks providers per capability × market over time. The adapter's obligation is to make that observation possible: honest provenance, honest freshness claims, honest failure reports. An adapter that shades its answers to look better breaks the feedback loop that keeps routing aligned with reality.

The through-line: **routing is invisible from both sides.** Consumers below the waterline never know routing happened; adapters above it never know where they stand in it. Only the Router holds the map, which is exactly what makes redrawing the map a non-event.

---

## 7. Data Quality

The quality dimensions — what they are and how each is defined — are platform vocabulary, specified in MARKET_DATA_PLATFORM.md §10: **Freshness, Reliability, Coverage, Latency, Completeness, Consistency**. This document adds the seventh, and the boundary-side view of how quality is actually produced.

**Trust** is the composite the other six feed: the platform's earned, evidence-based answer to "how much weight does this source's word carry, for this capability, in this market, today?" Trust is never granted by reputation, contract tier, or price paid — it is accumulated from observed behavior and spent by observed failures, exactly like the confidence machinery the platform already runs for its AI layers. A source that has shipped three years of consistent, complete Thai equity closes has high trust *for that*; the same source's sparse fund NAVs carry low trust *for that* — trust is never a per-vendor scalar, always a per-(capability × market) record.

How the platform evaluates providers, structurally:

- **Evaluation is passive and continuous.** Quality is measured from the ordinary flow of answers — validation outcomes (how often this source's data is quarantined), calendar checks (how often expected observations are missing), cross-source comparison where overlap exists (how often this source disagrees with higher-trust peers), and revision detection (how often it silently rewrites its own past). No special test traffic; the work *is* the test.
- **The adapter's role is honest instrumentation, not self-grading.** Adapters attach provenance, timing, and failure detail to every answer; the platform computes quality from what actually happened. A provider never scores itself — the same never-grade-your-own-work separation the platform's evaluation layers enforce everywhere else (an evaluation layer that can be influenced by its subject is not an evaluation layer).
- **Quality judgments act on routing, never on data.** A degraded source is demoted, quarantined-from, or retired for the affected capability × market; its already-canonical observations are never retroactively "corrected," because the platform records what it observed, honestly, forever. If accumulated evidence shows a stretch of canon was bad, the remedy is a new, explicit, provenance-tagged repair through the platform's existing correction discipline — new records, never edits.

---

## 8. Failure Handling

The external world fails constantly; MARKET_DATA_PLATFORM.md §11 defines how the *platform* degrades. This section defines the adapter-side half: what a well-behaved adapter does at the moment of failure, so the platform's graceful degradation has honest raw material to work with. One rule generates every row: **an adapter's job in failure is accurate reporting, not heroic recovery.**

- **Provider Offline** — the adapter reports unreachability promptly and specifically. It does not retry indefinitely (turning an outage into a hang), does not serve remembered answers as fresh (adapters hold no authoritative state — §3), does not guess. The Router walks the fallback order; that is the recovery, and it lives above the adapter.
- **Rate Limit** — reported as a distinct condition, not disguised as an outage, because the platform's correct responses differ: back off and reschedule for a rate limit, fail over for an outage. An adapter that burns its budget on uncoordinated retries makes the limit worse; pacing discipline is part of the contract.
- **Partial Data** — the answer arrives with an explicit accounting: what was asked, what was returned, what is absent. A silently partial answer is the most dangerous failure in the catalog, because it *looks* like success — and the calendar-aware validation that would catch it works far better when the adapter confesses the gap than when the gap must be inferred.
- **Missing Symbols** — "I don't know this instrument" is a clean, honest, per-item answer — never an error that poisons a batch, never a fuzzy match to something similar. Nearest-match guessing at the adapter level is identity assertion by the back door (§2), and identity is the one domain where guessing is forbidden outright.
- **Incomplete History** — a series with holes is delivered as a series with *declared* holes. The adapter never interpolates, never splices another source's data into the gaps (cross-source composition is the Router's decision, recorded in provenance), never trims the range to hide the ragged edge.
- **Currency Missing** — an observation without a trustworthy currency label is reported as exactly that — not defaulted to the market's usual currency. A wrong price is one bad number; a right number in a wrong currency is a systematic mis-valuation by an exchange rate, and validation can only catch what the adapter didn't paper over.
- **Corporate Action Delay** — an adapter that observes price-series effects before the explaining event simply reports what it sees, promptly and without adjustment. Detecting the incoherence and quarantining the affected span is validation's job; the adapter's contribution is speed and fidelity of the raw claims.

The shape across all seven: failures at this boundary are **contained, classified, and confessed** — contained so one provider's bad day never blocks the pipeline, classified so the platform chooses the right response, confessed so degradation is visible all the way up (PLATFORM_EVOLUTION.md invariant 9). The deterministic core never sees any of this weather; that promise is kept *here*, at the first boundary the weather hits.

---

## 9. Caching Ownership

Cache design — what is kept, for how long, and why settled history is a permanent record rather than a cache — is specified in MARKET_DATA_PLATFORM.md §12. This section fixes the single question that boundary discipline turns on: **who owns what.**

The rule: **all caches of external data live in the Market Data Platform, below the canonical boundary and above the adapters. Adapters own no caches; engines own no caches.**

- **Search Cache** — Market Data Platform. Short-lived convenience over search results; never identity.
- **Metadata Cache** — Market Data Platform, subordinate to the Registry's stewarded record.
- **Price Cache (latest)** — Market Data Platform, freshness governed per asset-capability.
- **History Cache** — Market Data Platform; settled observations, effectively permanent, the store that makes replay provider-independent.
- **FX Cache** — Market Data Platform; volatile tip, immutable history, identical standard.
- **Benchmark Cache** — Market Data Platform; permanent like price history, because evaluation must be as reproducible as the returns it judges.

Why adapters hold no caches: an adapter cache is invisible state between the platform and the truth. It quietly re-serves answers the platform believes are fresh, survives across requests in ways provenance doesn't capture, and — worst — makes two adapters for the same provider disagree with each other. The adapter's statelessness (§3) is what makes its answers *mean* something: every answer is what the provider says now, or an honest failure. (Transport-level courtesy toward a vendor's rate limits is the adapter's business; a store the platform's freshness reasoning doesn't know about is not.)

Why engines hold no caches: a private engine cache is a second source of truth with an undocumented refresh policy — the precise duplication ADR-004 forbids, wearing a performance costume. Engines read canonical data; one layer, one policy, decides how canonical data is kept warm, fresh, and permanent.

Ownership in one line: **adapters remember nothing, the platform remembers everything, engines remember only what the platform tells them.**

---

## 10. Extensibility

The acceptance test for this entire document: integrating a new provider — or retiring an old one — is an event *entirely contained* between the External World and the Provider Interface. Walking the claim through every protected engine:

- **Portfolio Engine** — consumes canonical stored observations keyed by `asset_id`. A new provider changes which source *produced* future observations (recorded in provenance); it cannot change what an observation *is*. No change, by construction.
- **Replay Engine** — replays ledgers against settled canonical history, which is permanent and provider-independent (§9). A provider added in 2028 cannot alter what 2026 recorded; a provider retired in 2028 cannot take its contributed history with it. No change, by construction.
- **Analytics** — computes over canonical series through the one metrics implementation. New provider, better coverage, same formulas. No change.
- **AI Evaluation** — grades recorded recommendations against recorded outcomes and benchmarks — all canonical, all immutable. A provider event can improve the *future* quality of benchmark data; it cannot touch a single recorded grade. No change.
- **Optimizer** — forms beliefs over canonical scores and observations under OPTIMIZER_PHILOSOPHY.md's constitution, which never names a data source. Fresher inputs, identical machinery. No change.

What integration actually consists of: **write one adapter** (teach the platform the vendor's dialect — §4, the whole job), **declare capabilities honestly** (§5), **let routing incorporate it** (initially low-trust, earning primacy through observed quality — §6, §7). Retirement is the mirror image: remove the adapter, let routing re-rank, keep every observation the provider ever contributed — provenance-tagged, canonical, permanent. And when a genuinely *new kind* of source arrives (streaming, broker quotes, exchange feeds, alternative data — MARKET_DATA_PLATFORM.md §13), the extension lands in the shared vocabulary: a new capability word, possibly a new canonical observation kind, added once, openly — never as one adapter's private dialect leaking upward. Either way, the five engines above learn nothing, because there is nothing below the waterline to teach.

---

## 11. Design Principles

1. **Providers are replaceable; only their provenance is permanent.** Any source able to observe the same facts is a substitute. What a provider leaves behind is canonical observations tagged with its name — never a dependency on its existence.
2. **Business logic depends only on canonical models.** No engine, analytic, or AI layer can name a provider, parse a vendor shape, or behave differently by source except through recorded provenance and quality.
3. **Normalize once — inside the adapter, before the boundary.** The vendor dialect dies at the interface. No raw mode, no exceptions, no "temporary" passthrough.
4. **Validate once — in the platform, after the boundary.** Adapters translate; they never judge. One rulebook, applied to one canonical shape, for every source equally.
5. **Never leak provider-specific concepts.** Not a field name, not a symbol convention, not a timezone habit, not an error code. Indistinguishability of sources downstream is the measurable definition of success.
6. **Capability over implementation.** Providers are described by what they can do, per market — and the describing table is the only thing that changes when the provider universe does.
7. **Adapters isolate change.** Every vendor event — new API version, new format, new provider, dead provider — is one adapter's maintenance, invisible above the interface. The adapter layer exists to be rewritten so nothing else ever is.
8. **Adapters are witnesses, not authorities.** They report observations with honest labels; they never assert identity, never fill gaps, never grade themselves, never hold state the platform can't see.
9. **Failure is confessed, not concealed.** Every degraded answer says so, specifically. A gap is recoverable; a plausible fabrication accepted into canon is a defect replay reproduces forever.
10. **Trust is earned per capability, per market, from evidence.** Never granted by reputation, never global per vendor, never allowed to edit what was already honestly recorded.

---

## Related Documents

- [PLATFORM_EVOLUTION.md](PLATFORM_EVOLUTION.md) — the platform invariants this boundary enforces at its outermost edge
- [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md) — asset identity: the authority no provider may ever hold
- [MARKET_DATA_PLATFORM.md](MARKET_DATA_PLATFORM.md) — the consuming platform: pipeline, canonical models, routing, validation, quality, caching
- [PORTFOLIO_DOMAIN_MODEL.md](PORTFOLIO_DOMAIN_MODEL.md) — the portfolios whose determinism this boundary ultimately protects
- [../engineering/DECISION_LOG.md](../engineering/DECISION_LOG.md) — the recorded provider incidents (settlement-price lag, DR symbol normalization) that motivated drawing this boundary once, properly
