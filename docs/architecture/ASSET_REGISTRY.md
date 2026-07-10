# Asset Registry

_The single authoritative source of asset identity: the permanent identity layer between external providers and internal portfolio accounting, guaranteeing that one real-world financial instrument always maps to exactly one internal Asset._

_This is not a database design, not an implementation guide, and not an API specification. [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md) defined what an Asset **is** — the universal model, capabilities, and transaction vocabulary — and named the Registry as its keeper. [MARKET_DATA_PLATFORM.md](MARKET_DATA_PLATFORM.md) defined the pipeline that carries observations toward the core, including the Resolver's evidence hierarchy. This document defines the **institution** both of them presuppose: the one authority allowed to decide which real-world instrument any piece of evidence is about. Where those documents described identity from the outside — as a field on a model, as a stage in a pipeline — this one describes it from the inside: how identity is minted, defended, related, and kept permanent._

_Read together with [PLATFORM_EVOLUTION.md](PLATFORM_EVOLUTION.md) (the invariants), [PROVIDER_INTERFACE.md](PROVIDER_INTERFACE.md) (the witnesses whose evidence the Registry adjudicates), and [PORTFOLIO_DOMAIN_MODEL.md](PORTFOLIO_DOMAIN_MODEL.md) (the accounting boundaries whose determinism depends on identity never moving)._

---

## 1. Philosophy

### Symbols are not identities

A symbol is a name, and a name lives in somebody's namespace. `ADVANC`, `ADVANC.BK`, an ISIN, a broker's internal code — each is a coordinate in a different naming system, maintained by a different institution, for that institution's own purposes, on that institution's own schedule. Namespaces collide (the same four letters mean different instruments on different exchanges), recycle (exchanges reissue tickers after delistings), drift (vendors invent suffix conventions — the platform's own decision log records a depository-receipt spelling that had to be normalized at every call site), and disagree (two providers, one instrument, two spellings; one spelling, two instruments).

None of this is pathology. It is what names *are*: convenient, local, and impermanent. The problem begins only when a system that keeps permanent records — a transaction ledger that must replay identically forever — uses an impermanent name as if it were the thing itself. A ledger keyed by symbols inherits every future decision of every namespace owner: a recycled ticker silently welds two unrelated companies' histories together; a vendor's suffix change orphans years of records. **The ledger is forever; names are not; therefore the ledger may never be keyed by a name.** Identity must be something the platform itself mints, so that nothing outside the platform can move it.

### Providers do not own identities

A provider owns a *namespace* — its own catalog of symbols and records, built for its own product. When a provider answers a search, it is answering "what do *I* call the things that match this?" — never "what *is* this?" It cannot answer the second question, because the second question is about the platform's world: whether this instrument is already held in some ledger under an existing identity, whether it is a wrapper around something already registered, whether two claims arriving through different doors are one thing or two. Only a party that can see all the evidence, across all providers and all discovery doors, and that is accountable to the platform's own permanent records, can answer that — and no provider sees any of it.

This is why [PROVIDER_INTERFACE.md](PROVIDER_INTERFACE.md) §2 makes "never assert identity" the first of its never-do rules. A provider that names, merges, or splits platform assets has crossed from witness to judge — and a witness-judge whose testimony changes on a vendor's schedule would make the meaning of recorded history contingent on an outside party with no duty to the platform's invariants.

### One authority, because identity questions must have one answer

If two subsystems can each hold an opinion about what an instrument is, they will eventually disagree, and the disagreement will surface as money: a holding double-counted because two doors created two assets for one fund, or two companies' returns averaged because a ticker was recycled. The platform already knows the cure, because it applied it to accounting: the Replay Engine is the single accounting authority, and every metric derives from it (ADR-001, ADR-004). The Asset Registry is the same move applied to identity — **the one subsystem whose answer to "what is this?" is final**, which every other subsystem consumes and none may second-guess or shadow with a private mapping. One real-world instrument, one `asset_id`, one place that guarantees it.

---

## 2. Responsibilities

### What the Registry owns

- **Asset identity** — minting `asset_id`s, and the guarantee that gives minting meaning: one real-world instrument maps to exactly one, forever. Everything else in this list exists to keep that guarantee true.
- **Canonical symbol** — assigning the platform's own stable, human-readable name at registration, and the discipline that it is assigned once and never reassigned (§3).
- **External identifiers** — custody of every external name the asset is known by (ISIN, CUSIP, SEDOL, FIGI, exchange tickers, provider symbols, broker codes): recording them as evidence, mapping them to the `asset_id`, and — critically — keeping mappings that no longer apply, because a ticker retired in 2024 must still resolve correctly when a 2023 statement is imported in 2028.
- **Exchange mapping and listing information** — which venue an asset trades on, in which currency, under which local conventions; and for multi-listed instruments, which listing *this* `asset_id` is (§5).
- **Lifecycle** — where each asset stands (§6), from candidate claim to archived record, so every engine can ask "can anything still happen to this?" without knowing why the answer changed.
- **Classification** — stewardship of the descriptive taxonomy (§8): asset class, sector, region, currency, and the rest of the vocabulary that analytics and policy evaluate.
- **Relationships** — the explicit links between distinct identities: a DR and the share it wraps, two listings of one economic entity, a merged asset and its successor, a derivative and its underlying. Relationships are how the Registry expresses "related but not the same" without ever blurring identities together.

### What the Registry must never own

- **Prices and observations.** The Registry says what an asset *is*; the Market Data Platform says what it is *worth* and what happened to it. An identity record with a price inside it is two authorities in one body.
- **Accounting state.** Holdings, cost basis, and transactions belong to the ledger and the Portfolio Engine. The Registry knows that an asset *can* be held, never whether or where it *is* held.
- **Business judgment.** Whether an asset is a good investment, fits a portfolio's universe, or should be bought is the domain of Portfolio Policy, the Optimizer, and the human — consumers of the Registry's facts, never functions of it (§8).
- **Provider communication.** The Registry adjudicates evidence; adapters gather it. A Registry that calls vendors directly has dissolved the waterline PROVIDER_INTERFACE.md exists to hold.
- **The meaning of history.** The Registry records identity events going forward; it never rewrites what a ledger already recorded. Its authority is over *what things are*, not over *what happened*.

---

## 3. Identity Model

The identity model is a two-tier structure: a small permanent core the platform owns, surrounded by a growing evidence file the world supplies.

### The permanent tier — platform-owned, never moves

- **`asset_id`** — opaque, internal, minted once at registration (§6), never reused, never derived from any external name. The only identity business logic may hold. Its opacity is deliberate: an identifier with no embedded meaning has nothing that can go stale.
- **`canonical_symbol`** — the platform's own human-readable name, assigned once at registration and never reassigned — even if the asset is later renamed on its home exchange. It exists so a person, a log line, or a document can reference an asset without the opaque `asset_id` and without reintroducing provider-symbol ambiguity. If the world renames an instrument, the platform records the new name as display and evidence; the canonical symbol stays put, because a reference written five years ago must still mean what it meant.

Permanence is a property only the platform can grant. Every external registry — however authoritative in its own domain — reserves the right to reassign, retire, or restructure its identifiers, and exercises it. The platform is the only party accountable to its own ledger, so the platform is the only party that can promise an identifier will mean the same thing for as long as the ledger exists.

### The evidence tier — externally owned, mutable, plural

- **`display_symbol`** — cosmetic, presentation-only, freely changeable, possibly different per user or context. The one identifier with *no* evidentiary weight: it follows the world's current naming for human comfort and asserts nothing.
- **`provider_symbol`** — each provider's own spelling, recorded per provider as a mapping *into* the `asset_id`. Meaningful only inside that provider's universe; translated on arrival, never stored as identity, retained historically after a provider is gone.
- **ISIN** — the strongest single external claim: globally scoped, issuance-assigned. But it identifies the *security*, not the *listing* — one ISIN can trade on several exchanges in several currencies — so ISIN narrows the world to a security and context must still pick the listing.
- **CUSIP / SEDOL** — strong inside their home registries (North American clearing; UK/Ireland reference), absent elsewhere. Regional strength, honestly bounded.
- **FIGI** — listing-granular where ISIN is security-granular, which matches the platform's own unit of identity (§5) unusually well, and openly licensed. Valuable evidence — and still evidence: an external registry's opinion, adopted as a clue, never as the key.
- **Exchange identifiers** — the venue's own listing codes and local ticker, decisive *in combination with* the venue and market, weak alone (tickers recycle).
- **Broker codes** — proprietary, undocumented, occasionally reused; the weakest class of evidence, resolvable only through accumulated confirmed mappings.

The two tiers never trade places. No external identifier — not even an ISIN — is ever promoted to being *the* identity, because every one of them has an owner who is not the platform. And the permanent tier never flows outward as evidence: `asset_id` appears in no provider conversation, because it means nothing outside the waterline. External names flow in and are weighed; canonical identity flows out and is used; the arrow never reverses (UNIVERSAL_ASSET_ARCHITECTURE.md §3).

---

## 4. Symbol Resolution

The resolution *pipeline* — discovery doors, the evidence hierarchy and its weighing, the worked ambiguities — is specified in MARKET_DATA_PLATFORM.md §4–5. This section defines the Registry's side: resolution as an act of **adjudication**, whose verdicts the Registry alone may enter into the permanent record.

### The adjudication sequence

- **A claim arrives.** A user search, a CSV row, a broker feed line, a provider search result, a manual entry — each is a bundle of evidence ("here is everything observed about something"), never an instruction to create anything.
- **Candidate matching.** The claim's identifiers are compared against the Registry's existing mappings — current *and historical*. The first question is always "is this something we already know?", because the failure mode that most threatens the one-instrument-one-asset guarantee is not misnaming a new asset; it is minting a second identity for an old one.
- **Evidence gathering.** When the initial claim is thin (a bare ticker from a CSV), the Registry may request corroboration through the Market Data Platform — provider lookups whose answers are more evidence, weighed by the source's earned trust (PROVIDER_INTERFACE.md §7), never verdicts.
- **Confidence.** Accumulated evidence yields one of three honest positions: **decisive** (identifiers converge on exactly one existing asset, or clearly describe something genuinely new), **ambiguous** (multiple plausible matches, or a new/existing question that evidence cannot settle), or **unknown** (nothing matches and nothing corroborates).
- **Verdict.** Decisive evidence resolves silently — mapped to the existing `asset_id`, or registered as new. Ambiguity is **surfaced**: a ranked candidate list, a user confirmation, a quarantined claim — never a silent guess, because a wrong price is a bad day but a wrong identity poisons the ledger, and the ledger is forever.
- **Canonical mapping.** Every confirmed resolution — silent or human-assisted — is recorded as a durable mapping, so the same question is never asked twice and the same string resolves the same way through every future door.

### Conflict resolution

When evidence *conflicts* — two providers assert different ISINs for one symbol, a broker code matches one asset while the accompanying name matches another — the conflict itself becomes a first-class record. The Registry never averages testimony, never lets the higher-volume or more recently heard source win by default, and never auto-picks under genuine conflict. Rules resolve what rules can (identifier hierarchy, market context, earned source trust); everything else escalates to the human, whose confirmation is then recorded so the conflict is settled once. This is the platform's judgment/arithmetic boundary applied to identity: mechanical evidence-weighing is arithmetic; deciding what a thing *is* under real ambiguity is judgment, and judgment is exercised deliberately and recorded.

### Why providers never resolve identity

Resolution assigns permanent meaning inside the platform's world, and every input to that assignment is one party's fallible testimony. Letting a provider resolve identity collapses witness and judge into one: the provider's namespace errors become ledger errors, its symbol conventions become platform semantics, and its disappearance takes the platform's self-knowledge with it. Adapters therefore return candidates and descriptions — raw material for adjudication — and the verdict is always entered by the Registry, the only party that can see all the evidence and the only party the ledger can hold accountable.

---

## 5. Multiple Listings

### The unit of identity is the listing

The Registry's doctrine for every multi-listing situation follows from one decision: an `asset_id` identifies a **tradable instrument in a specific venue and currency** — a listing — not a corporation, a brand, or an economic idea. The reason is accounting: two listings of one company have different currencies, calendars, closing prices, settlement cycles, and corporate-action timing. Those are precisely the facts the Portfolio Engine and Replay Engine compute with; where the accounting facts differ, the identities must differ, or determinism is lost to a hidden aggregation.

What binds listings of one economic entity together is not a shared identity but an explicit, recorded **relationship** — a link between distinct `asset_id`s that analytics may traverse and accounting never does.

### The cases

- **Dual-listed companies.** One economic entity, genuinely different listings — a US ADR and Hong Kong ordinary shares trading under the same famous ticker. Two `asset_id`s, one *same-entity* relationship. A user holding both holds two positions in two currencies on two calendars; the "one company" view is an analytics aggregation over the relationship, computed on demand, never a merge of records.
- **Depositary Receipts — ADR, GDR, local DR.** A DR is a distinct instrument that *wraps* another: its own listing, currency, fees, and quirks, with its own `asset_id`, joined to the underlying by a *wraps* relationship. The platform learned this one empirically — a vendor's DR symbol convention once had to be normalized at every call site precisely because DR and underlying were entangled in symbol space. The Registry makes the distinction structural: never silently substitute a DR for its underlying, in either direction, because they are related and *not the same*.
- **Cross-listed ETFs.** One fund structure, several exchange listings. Each listing is its own `asset_id` (its own price series, currency, calendar); the shared fund is a relationship among them. This also resolves the dual-pricing wrinkle cleanly — a listing can carry both market OHLC and fund NAV capabilities without any identity gymnastics.
- **Regional listings.** The general case of all the above: the same security admitted to several venues. ISIN says "same security"; venue and currency say "different listing"; the Registry records both truths at their proper levels — one relationship, several identities.

### How identity is preserved

Preserved, in every case, by refusing the two tempting shortcuts. The Registry never **collapses** related listings into one identity (which silently mis-books currency, calendar, and price differences into the ledger), and never lets resolution **drift** between them (a symbol that could mean the ADR or the ordinary resolves by market context or explicit user choice — never by guess, per §4). Relationships carry the sameness; identities carry the differences; and every engine downstream gets exactly one unambiguous `asset_id` per position, forever.

---

## 6. Asset Lifecycle

The lifecycle has two distinct phases with a bright line between them: **states of a claim**, before identity exists, and **states of an asset**, after identity exists and can never be destroyed.

### Before identity — states of a claim

- **Discovery** — an encounter has produced a claim: evidence that something exists, from any door (search, import, feed, manual entry). Nothing permanent has been created; discovery never mints (MARKET_DATA_PLATFORM.md §4).
- **Candidate** — the claim is under adjudication (§4): being matched against known assets, gathering corroboration, possibly awaiting a human's word on an ambiguity. A candidate has no `asset_id`; it can be resolved into an existing asset, promoted to a new one, or discarded as noise — all without leaving a scar, because nothing referenced it yet.
- **Verified** — adjudication concluded the instrument is real, distinct, and sufficiently described. **This is the moment of minting**: `asset_id` created, `canonical_symbol` assigned, evidence file attached. Everything before this moment was reversible; nothing after it ever is.

### After identity — states of an asset

- **Active** — the normal state: tradable, priceable, referenceable in ledgers.
- **Suspended** — temporarily not tradable (a halt, a market suspension); holdings unaffected, valuation continues as data allows, new transactions refused. Fully reversible.
- **Delisted** — permanently off its home venue. Still a valid identity for as long as any ledger references it — and after, since references never expire. Delisting changes what may happen *next*, never what already happened.
- **Merged** — the asset's ongoing economic life continues under a successor `asset_id`, recorded as a forward-looking relationship with its effective date. The merged-away identity is never deleted or redirected retroactively: pre-merge history references it forever, and replays of that history are untouched by the merge.
- **Archived** — no live position references the asset and no data flows for it; the Registry keeps the full record anyway — identity, evidence file, historical mappings, relationships. Archived is a statement about *activity*, never about *existence*. Closed is not deleted, here as everywhere in the platform.

### Identity permanence

The permanence rule is not a preference; it is entailed by two commitments already made elsewhere. The ledger is immutable (ADR-001; PLATFORM_EVOLUTION.md invariants), and the ledger references assets by `asset_id`. If any lifecycle transition could destroy or reassign an `asset_id`, some immutable ledger row would come to reference nothing — or worse, reference something else. Therefore every post-minting state, however terminal it feels, is a *status on* a permanent identity, never an *end of* one. Assets are born once, exactly once, and never die; they only stop having a future.

---

## 7. Validation

Registry validation defends one guarantee — one real-world instrument, one `asset_id` — against the specific ways the world tries to break it.

- **Duplicate detection.** The same instrument arriving through two doors (a fund via CSV on Monday, via broker feed on Thursday) must converge on one identity. The defense is structural — every claim passes candidate matching against current and historical mappings before minting is even considered — plus continuous auditing: when identifier overlap between two *already registered* assets is discovered later, that is a surfaced finding for adjudication and, if confirmed, an explicit merge (§6) — never a silent cleanup, because both identities may already be load-bearing in ledgers.
- **Conflicting identifiers.** One asset carrying two ISINs, or one ISIN claimed by two assets, is a contradiction in the evidence file. The Registry records the conflict as a first-class finding, keeps both claims with their provenance, resolves by rule where rules suffice and by human where they don't (§4) — and never silently discards the inconvenient claim, because the discarded claim is exactly what the next import will arrive holding.
- **Provider disagreement.** Sources disagreeing about descriptive facts (name, classification, listing venue) is ordinary weather, weighed by earned trust and stewarded (§8). Sources disagreeing about *identity-bearing* facts (identifiers, what a symbol denotes) is a resolution conflict and gets the full adjudication treatment. The Registry distinguishes the two sharply: metadata disagreement lowers confidence in a fact; identity disagreement freezes the mapping until settled.
- **Missing identifiers.** Absence is data, judged against the asset's kind. Property with no ISIN is correct — the honest shape of an asset class outside the identifier system (the manual-entry proof case). An exchange-listed equity with no ISIN after corroboration is a *confidence problem*: registerable when the user or context vouches for it, but flagged, and expected to accumulate identifiers as evidence arrives. Validation asks "is this absence expected for this kind of thing?" — never "is every field filled?"
- **Corporate action impacts.** Corporate actions are where identity errors are most likely, because the world's names move while the thing persists — or the thing genuinely changes while names persist. A symbol change is the same asset with a new external name (evidence file updated, `asset_id` and `canonical_symbol` untouched). A merger or share-class conversion is a *successor* relationship between identities. A spin-off is a *new* identity related to its parent. The Registry's discipline is to classify which of these a claimed event is **before** updating any mapping — and to quarantine resolution for the affected names when the evidence is still incoherent (price effects observed before the explaining event), in step with the validation quarantine of MARKET_DATA_PLATFORM.md §8.

### The validation philosophy

The Ledger Validator's stance, applied one layer down: **detect loudly, repair explicitly, never auto-correct what is load-bearing.** Identity errors are worse than data errors because they are multiplicative — one wrong mapping mis-books every subsequent observation and transaction that flows through it. So the Registry treats suspicion as a surfaced finding with provenance, treats every repair as an explicit, dated, recorded act (a merge, a remapping, a relationship), and treats silence as the one response that is never acceptable. A gap in the evidence file is recoverable; a plausible wrong identity accepted into the ledger is a defect that replay reproduces forever.

---

## 8. Classification

### The classified dimensions

Classification is the descriptive taxonomy the Registry stewards on top of identity — the vocabulary in which analytics, attribution, policy, and the optimizer reason about assets:

- **Asset Class** — equity, fund, fixed income, precious metal, digital asset, cash, real property — aligned with `asset_type` in the universal model and deliberately coarse.
- **Sector / Industry** — the business taxonomy, at two levels of grain. The platform already runs a stewarded sector system for its home market; classification generalizes that precedent rather than inventing a parallel one.
- **Region / Country** — economic geography, which is not the same as listing venue (a company can list in one country and earn in another; both facts are recordable, at their proper levels).
- **Currency** — the asset's native pricing and settlement currency: universal-model fact, classification dimension, and FX trigger all at once.
- **Exchange** — the listing venue, per §5 a component of identity itself for listed instruments, and a filterable dimension for everything downstream.
- **Investment Universe compatibility** — the *facts* universe rules evaluate: market membership, asset class, currency, tax-wrapper qualification (the retirement-fund and tax-privileged fund categories the platform already models), income character. The Registry publishes these facts; PORTFOLIO_DOMAIN_MODEL.md §4's universes consume them. The Registry never decides whether an asset belongs in a given portfolio — it makes the question answerable. **Registry describes; Portfolio Policy judges.**

### Stewardship

Classification is where the Registry's authority is *curatorial* rather than *adjudicative* — and the distinction shapes everything:

- **One taxonomy, many witnesses.** Providers classify assets in their own vocabularies, and they disagree. The platform maintains one canonical taxonomy and maps provider classifications into it as evidence — the same normalize-at-the-boundary move made for symbols, applied to categories. No engine ever branches on a vendor's category string.
- **Mutable, unlike identity.** Classifications legitimately change — companies are re-sectored, funds change mandates, a market is reclassified between emerging and developed. The Registry updates the classification as a **dated fact against the permanent identity**, and retains the history, so that analytics computing over a past period can see the classification *as it stood then*. Identity never moves; descriptions move on the record.
- **Confidence, not just values.** A classification sourced from three concurring high-trust providers and one confirmed by a user carry different weight than one inferred from a single feed. Stewardship tracks where each classified fact came from — the platform-wide provenance discipline, applied to descriptions.

---

## 9. Relationship with Providers

The relationship is a single asymmetry, stated three ways across three documents and enforced here: **providers supply evidence; the Registry decides.** (PROVIDER_INTERFACE.md §2 states it from the adapter's side; MARKET_DATA_PLATFORM.md §5 from the pipeline's side; this is the authority's side.)

What flows in: search candidates, descriptive metadata, identifier claims, corporate-action observations, classification opinions — all provenance-tagged, all weighed by the source's earned trust per capability and market, none self-executing. A provider's claim, however confident, is an *input to* a Registry decision, never a decision.

What can never flow in:

- **A provider cannot rename an asset.** A vendor changing its spelling changes a `provider_symbol` mapping — one row in the evidence file. If the *world* renamed the instrument, corroborated evidence prompts a Registry rename event: display and evidence updated, `asset_id` and `canonical_symbol` untouched. The provider's claim can *prompt* the event; only the Registry can *perform* it.
- **A provider cannot merge assets.** A vendor consolidating two records in its catalog is a fact about its catalog. A platform merge is an identity event with ledger consequences, performed only through §6's explicit, dated, human-confirmable process.
- **A provider cannot delete assets.** A vendor dropping coverage means one witness went quiet — a routing and quality event above the waterline, not an identity event below it. The asset, its evidence file, and its historical mappings persist untouched.

And the corollary that proves the design: **a provider's disappearance is an identity non-event.** Its symbols remain in the evidence file as historical mappings (still resolving correctly for old statements), its contributed observations remain canonical and provenance-tagged, and every `asset_id` it ever helped establish means exactly what it meant. The Registry is what makes providers replaceable — identity is the one thing that would otherwise chain the platform to its vendors, and the Registry is where that chain is cut.

---

## 10. Relationship with Portfolio

### The ledger stores `asset_id`, never symbols

Every transaction, holding, and snapshot references assets by `asset_id` alone. This is the load-bearing joint of the entire architecture: the ledger is the platform's single source of truth and is immutable (ADR-001), so whatever the ledger uses as a key must mean the same thing on every future day it is read. Symbols cannot promise that — they are other people's names (§1). The `asset_id` can, because the Registry exists to keep the promise.

### Replay depends only on `asset_id`

The Replay Engine's contract — same ledger, same prices, same result, forever — holds only if every input's meaning is fixed. A ledger row saying *asset X, quantity Q* replays identically in 2026 and 2036 because X is a platform fact no vendor, exchange, or rename can move. Had the row said `ADVANC.BK, 100`, replay would silently depend on what that string happens to denote — in some vendor's namespace, on the replay date — and determinism would be a property of the engine *plus the outside world's naming history*. Every Registry discipline in this document (permanence, historical mappings, listing-level identity, explicit merges) exists so replay never has to ask anyone what a name used to mean.

### Business logic never depends on provider symbols

The platform-wide rule (GLOSSARY.md: Business Logic), enforced by topology: engines below the Registry receive resolved `asset_id`s with universal fields and capability flags — never identifiers, never provider names (UNIVERSAL_ASSET_ARCHITECTURE.md §8). Symbols exist at exactly two places: the *boundary*, as resolution inputs (§4), and the *presentation surface*, where `display_symbol` is looked up at render time for human eyes. Between those two edges — through every engine, rule, and calculation — assets travel under platform identity alone. A symbol in business logic is a provider opinion smuggled below the waterline, and the audit for it is simple: no engine should be able to tell what any asset is *called*.

---

## 11. Future Expansion

The Registry supports every future asset class without redesign for one structural reason: **identity is minted, not derived.** An `asset_id` never depended on any particular identifier existing — ISINs, tickers, and exchanges are evidence *when present* (§3), and absence is data (§7). So each new class is a question of what its evidence file looks like, never of whether the identity model fits:

- **Funds** — identity anchored by ISIN and local fund registries; no continuous exchange in the usual sense; NAV-cycle pricing already first-class. Wrapper qualifications (retirement and tax-privileged categories) are classification facts (§8) evaluated by portfolio policy — the Registry describes the wrapper; the portfolio enforces it.
- **Bonds** — the identifier-richest class (ISIN-anchored per issue) and the first with a *scheduled* lifecycle: maturity is a known-in-advance terminal status, and a call is an early one. Both are §6 statuses on permanent identities — a matured bond's ledger history replays untouched, exactly like a delisted stock's.
- **Crypto** — the inverse extreme: no ISIN, no issuer, no exchange in the traditional sense, dozens of venue-specific pair spellings. The Registry *defines* the canonical asset by convention and maps every venue symbol to it — the pure case of minted-not-derived, already proven by the resolution model (MARKET_DATA_PLATFORM.md §5's convention-based case).
- **Property** — zero external identifiers, no venue, user-declared existence: identity rests entirely on the manual-entry door and the owner's description. The degenerate case that proves the design — a Registry that *required* external evidence could not register a house; this one records honest absence and moves on.
- **Options** — identity is *coordinates*: underlying `asset_id` + strike + expiry + exercise style. Each contract is its own `asset_id`; the *derivative-of* relationship (§5's machinery, one new relationship kind added openly per UNIVERSAL_ASSET_ARCHITECTURE.md §11) ties it to its underlying; expiry is a scheduled terminal status like a bond's maturity.
- **Futures** — the same coordinate pattern (root + delivery month + venue), each contract a distinct identity, plus one honest new concept: the *contract series*, a relationship threading successive expiries so analytics can see continuity while accounting sees — correctly — a sequence of distinct instruments. A roll is two transactions against two `asset_id`s, never a mutation of one.
- **Private Equity** — sparse evidence (perhaps a legal name and a document), no market, appraisal-based valuation. Identity-wise it is property with a different wrapper: minted from a claim, thin evidence file, honest absences.
- **Alternative Assets** — collectibles, physical holdings, whatever arrives next: some mixture of the above patterns. The Registry's question for any newcomer is never "does it have the right identifiers?" but only "can it be described, and is it distinct?" — and anything ownable can answer that.

The pattern across all eight: expansion adds **evidence shapes, statuses, and relationship kinds** — vocabulary, added openly, at the edges. The core act — mint a permanent identity, attach evidence, guarantee uniqueness — is identical for a Thai bank stock and an option contract, which is exactly why the engines downstream of the Registry never learn that expansion happened.

---

## 12. Design Principles

1. **One real-world instrument → one `asset_id`.** The Registry's entire purpose in one line; every mechanism in this document exists to keep it true through every door, provider, and corporate action.
2. **Symbols are evidence, never identity.** Every external name — ISIN included — is one party's fallible, mutable testimony, weighed at the boundary and recorded in the evidence file, never used as a key.
3. **Identity is permanent.** `asset_id` and `canonical_symbol` are assigned once and never reassigned, reused, or destroyed — because the immutable ledger references them, and the ledger is forever.
4. **The Registry is authoritative.** Exactly one subsystem answers "what is this?"; no engine, import, or provider holds a private identity mapping alongside it.
5. **Providers observe; the Registry decides.** Evidence flows in from witnesses; verdicts are entered by the one judge accountable to the platform's own records. No provider renames, merges, or deletes an asset — ever.
6. **Business logic uses `asset_id` only.** Symbols live at the resolution boundary and the presentation surface; between them, no engine knows what any asset is called.
7. **The unit of identity is the listing.** Where accounting facts differ — venue, currency, calendar — identities differ; sameness is expressed as explicit relationships, never as merged records.
8. **Resolve decisively or ask — never guess.** Silent resolution requires decisive evidence; ambiguity is surfaced and the confirmed answer recorded once. A wrong identity poisons the ledger permanently, so guessing is forbidden at any confidence short of certainty.
9. **Absence is data.** An asset without an ISIN, a venue, or any external identifier at all is a valid, honestly described identity — the model fits what exists, not the other way around.
10. **Lifecycle changes status, never identity.** Minting is the one irreversible moment; everything after — suspension, delisting, merger, archival — is a dated fact layered onto an identity that never dies.
11. **Descriptions move on the record; identity never moves.** Classifications are stewarded, dated, provenance-tagged, and historically retained — mutable facts on a permanent spine.
12. **Expansion adds vocabulary, never surgery.** New asset classes bring new evidence shapes, statuses, and relationship kinds, added openly to the shared model; the act of identity itself never changes.

---

## Related Documents

- [ASSET_REGISTRY_RETROSPECTIVE.md](ASSET_REGISTRY_RETROSPECTIVE.md) — an engineering retrospective on why this architecture was built this way, what assumptions changed during implementation, and what remains
- [PLATFORM_EVOLUTION.md](PLATFORM_EVOLUTION.md) — the platform invariants (immutability, boundary normalization, loud degradation) the Registry enforces for identity
- [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md) — the Asset model, capability vocabulary, and identity stack the Registry keeps
- [MARKET_DATA_PLATFORM.md](MARKET_DATA_PLATFORM.md) — the discovery doors and resolution pipeline whose verdicts the Registry alone enters into record
- [PROVIDER_INTERFACE.md](PROVIDER_INTERFACE.md) — the witnesses: what adapters may report, and the identity line they may never cross
- [PORTFOLIO_DOMAIN_MODEL.md](PORTFOLIO_DOMAIN_MODEL.md) — the accounting boundaries whose determinism rests on `asset_id` never moving
- [../engineering/DECISION_LOG.md](../engineering/DECISION_LOG.md) — the recorded incidents (DR symbol normalization, provider quirks) that taught the platform why identity must be owned, not borrowed
