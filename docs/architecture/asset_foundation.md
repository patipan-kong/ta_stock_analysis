# Asset Foundation

_The domain constitution of Asset Foundation — the root domain — and the architectural blueprint for Phase 3 M6._

_**Status: draft, pending ratification.** Upon ratification this document becomes a level-2 Domain Constitution under [platform_architecture.md](platform_architecture.md) §11: supreme inside the Asset Foundation boundary, subordinate to the Platform Architecture at it, and binding on the domain's technical design documents ([ASSET_REGISTRY.md](ASSET_REGISTRY.md), [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md), [CORPORATE_ACTION_DOMAIN.md](CORPORATE_ACTION_DOMAIN.md)). It designs the domain, not the implementation: no schemas, no APIs, no code._

---

## 1. Purpose and Position

Asset Foundation answers one question, permanently and unambiguously, for every other domain: **what is this thing?**

The constitution places it at the root ([platform_architecture.md](platform_architecture.md) §6.1): it depends on nothing inside the platform, and everything depends on it. Every ledger event, every price, every recommendation, every grade is a statement *about an identified thing* — which makes identity errors the only class of error the platform cannot contain downstream. A wrong price is a bad day; a wrong number is found by replay; a wrong identity is *multiplied* by replay, forever, into every derivation that touches it.

The domain therefore has an unusual character among the nine: it is an **institution, not a pipeline**. It does not process a flow; it holds an authority. Other domains do things to data as data passes through them. Asset Foundation *is asked questions and adjudicates claims*, and its value is measured not in throughput but in the permanence of its answers. This character drives every design decision below: passive authority, closed vocabulary, minted-not-derived identity, and a refusal to guess.

One consequence is worth stating before anything else, because it disciplines the whole document: **Asset Foundation never calls upward.** It does not fetch prices, does not read ledgers, does not ask engines anything. Evidence flows *in* from the edges (through Connectivity & Ingestion and Market Intelligence acting as witnesses); answers flow *out* to everyone; the domain itself initiates nothing outside its boundary. A root domain that reaches upward has inverted the dependency law, and the inversion would be paid for in determinism.

---

## 2. Charter

### What Asset Foundation owns

Six things, exhaustively. Everything in this domain is one of these; anything not one of these is another domain's.

1. **Identity.** The asset identity space: minting permanent `asset_id`s, the guarantee that one real-world instrument maps to exactly one, the canonical symbol, the evidence file of external names, and the adjudication by which claims become identities. Identity is the domain's founding responsibility; the other five exist to keep it meaningful over time.
2. **Definition.** The asset-definition vocabulary: what an asset *class* can do — unit semantics, valuation cadence, flow types, capability flags, lifecycle vocabulary — expressed as behavior contracts that engines consume instead of type branches (§5).
3. **Classification.** The descriptive taxonomy: asset class, sector, region, currency of denomination, wrapper qualification, and dimensions not yet needed — stewarded as dated, provenance-tagged, historically retained facts on permanent identities.
4. **Lifecycle.** The state vocabulary of a thing's existence: the reversible states of a *claim* before identity, the permanent statuses of an *asset* after, and the bright line between them — so that every engine can ask "can anything still happen to this?" without knowing why the answer changed.
5. **Structural events.** The adjudicated interpretation of what the world does to instruments — splits, mergers, spin-offs, renames, delistings, redemptions: which event family an announcement belongs to, which identities it touches, and what consequences it *implies*. The interpretation is owned here; the consequences are owned elsewhere and are only ever proposed (§4.4, §6).
6. **Relationships.** The identity graph: the typed, recorded links between distinct identities — a receipt and what it wraps, two listings of one entity, a predecessor and its successor, a derivative and its underlying. Relationships are how the domain says *related but not the same* without ever blurring identities together.

### What Asset Foundation never owns

- **Worth.** Prices, histories, calendars, rates, regimes belong to Market Intelligence. An identity record with a price inside it is two authorities in one body.
- **What happened.** Transactions, holdings, cost basis, and every derivation of them belong to Ledger & Accounting. The domain knows an asset *can* be held; never whether, where, or how much.
- **The doors.** Adapters, feeds, file parsers, broker connections, and the proposal/review pipeline belong to Connectivity & Ingestion. Asset Foundation adjudicates what arrives; it never operates the machinery of arrival.
- **Judgment.** Whether an asset is attractive, suitable, or permitted in a universe belongs to Portfolio and Decision Intelligence. The domain makes those questions *answerable*; it never answers them. **Asset Foundation describes; policy judges.**
- **Consequences.** The ledger effects of structural events — a split's rescaling, a merger's conversion — are ledger events, entering through the ingestion gate like every other fact. The domain computes what the consequences *should be* and proposes; it never writes.
- **The meaning of history.** The domain records identity facts going forward. It never rewrites, reinterprets, or "corrects" what a ledger already recorded. Its authority is over what things *are*, never over what *happened*.

---

## 3. The Interior Map

The milestone brief proposed eight subdomains: Registry, Identity Resolution, Asset Definitions, Classification, Discovery, Lifecycle, Relationships, Corporate Actions. This document reorganizes them into **six**, and the three changes are the load-bearing decisions of the map:

**"Registry" is not a subdomain — it is the domain's institutional name.** The Registry is the authority that all six subdomains together constitute; carving it out as one subdomain among peers would imply the others hold authority beside it, which is exactly the fragmentation the domain exists to prevent. The word survives as the name of the institution ("the Registry decides"), never as a box on the interior map.

**Identity Resolution is not a peer of Identity — it is Identity's verb.** Resolution and adjudication are how identity is exercised, not a separate concern that could evolve independently. A subdomain boundary between "identity" and "resolving identity" would invite the two to drift — a stored identity model and a resolution pipeline with subtly different opinions. They are one subdomain with one owner.

**Corporate Actions is not a bridge domain — it is interpretation homed here, consequences exported.** [CORPORATE_ACTION_DOMAIN.md](CORPORATE_ACTION_DOMAIN.md) describes itself as a bridge "owning neither" destination. Under the nine-domain constitution there are no bridge domains: every concept has exactly one home. The resolution: the *interpretive* act — "what did the world just do to this instrument?" — is an identity question and lives in Asset Foundation, as the Structural Events subdomain. The announcements arrive as witness claims through Connectivity & Ingestion; the ledger consequences leave as proposals through the ingestion gate. What the level-4 document calls a bridge is, constitutionally, one subdomain with two well-behaved boundary crossings (§4.4). Nothing in that document's discipline changes; only its address does.

The six subdomains:

### 3.1 Identity

The founding subdomain: minting, permanence, the two-tier identity model (permanent tier platform-owned; evidence tier externally owned, plural, time-bounded), candidate matching against current *and historical* mappings, adjudication of claims — decisive, ambiguous, or unknown, never guessed — and the durable recording of every verdict so no question is ever asked twice. The unit of identity is the listing, because identity must differ wherever accounting facts differ. Interior law: [ASSET_REGISTRY.md](ASSET_REGISTRY.md) §§1–5, 7.

### 3.2 Definitions

The behavior-contract library — "assets are plugins," and this subdomain is the plugin library (§5 settles what a definition actually *is*). It owns the capability vocabulary, the unit and flow semantics per class, and the discipline that the vocabulary is closed, platform-owned, and extended only deliberately. Interior law: [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md) §§2, 5, 9–11.

### 3.3 Classification

The curatorial subdomain, distinct from Identity in the nature of its authority: identity is *adjudicative* (one answer, final), classification is *curatorial* (stewarded facts that legitimately change). Classifications are dated facts against permanent identities, historically retained so analytics can see the taxonomy *as it stood then*; provider taxonomies are mapped in as evidence, never adopted as vocabulary. Interior law: [ASSET_REGISTRY.md](ASSET_REGISTRY.md) §8.

### 3.4 Lifecycle & Structural Events

One subdomain, deliberately, because structural events are the principal force that moves lifecycle: a delisting is a state; the delisting *event* is what set it. It owns the claim states (Discovery → Candidate → Verified, all reversible), the asset statuses (Active, Suspended, Delisted, Merged, Archived — statuses on identities that never die), the minting moment as the one irreversible instant, and the interpretation of structural events into families whose classification precedes every consequence. Interior law: [ASSET_REGISTRY.md](ASSET_REGISTRY.md) §6; [CORPORATE_ACTION_DOMAIN.md](CORPORATE_ACTION_DOMAIN.md) — the whole document, re-homed per above.

### 3.5 Relationships

The identity graph: a small, closed, platform-owned vocabulary of typed edges — *wraps* (a DR and its underlying), *same-entity* (listings of one economic entity), *successor-of* (mergers, conversions), *spun-off-from*, *derivative-of* (reserved for the options era), and kinds not yet needed, added openly. Relationships carry the sameness; identities carry the differences. Analytics may traverse the graph; accounting never does — a relationship is never an instruction to aggregate, substitute, or convert. Interior law: [ASSET_REGISTRY.md](ASSET_REGISTRY.md) §5; [CORPORATE_ACTION_DOMAIN.md](CORPORATE_ACTION_DOMAIN.md) §4.

### 3.6 Catalog & Discovery

The read surface: the searchable, browsable catalog of everything the platform knows to be ownable. One clarification the milestone brief's "Discovery" conflated: discovery is two different things, and only one lives here. **Inbound** discovery — a claim arriving through a door (search result, CSV row, feed line) — is Connectivity & Ingestion's door plus Identity's adjudication; this subdomain plays no part. **Outbound** discovery — a human or a domain querying "what assets exist, matching what description?" — is this subdomain: a query surface over the domain's own recorded facts, owning ranking and findability, creating nothing, resolving nothing, minting never. Search that quietly mints is the fragmentation risk of §7.5 wearing a friendly face.

---

## 4. Boundaries

The general posture toward all domains: **answers flow out to everyone; evidence flows in only as witness testimony; instruction never flows in at all.** Per constitution §7.4, external and internal parties alike inform the domain that owns the question — and Asset Foundation owns the question "what is this?"

### 4.1 Market Intelligence

*Direction: Market Intelligence depends on Asset Foundation. Never the reverse.*

Every observation is a statement about an identified thing: prices, calendars, and regimes are keyed by `asset_id`, and Market Intelligence resolves provider symbols through Asset Foundation's mappings at its own boundary — no price ever travels under a vendor's name. In the other direction, Market Intelligence acts as a *witness*: corroboration lookups during adjudication, descriptive metadata, structural-event announcements from data feeds — all testimony, weighed by earned trust, never verdicts. Two prohibitions complete the contract: Asset Foundation never stores or serves worth (not even "last price" as a convenience), and Market Intelligence never mints, merges, or renames. Read-time price adjustment across splits — back-adjustment for charting — is presentation of *observations* and belongs entirely to Market Intelligence, keyed off the structural-event record this domain publishes.

### 4.2 Ledger & Accounting

*Direction: Ledger & Accounting depends on Asset Foundation — in the deliberately frozen way constitution §6.3 prescribes.*

Ledger events reference permanent identities, resolved *before* recording; replay never re-resolves, and the accounting path consults no live authority — transaction-time validation reads the domain's *recorded* state (definition, capabilities, lifecycle status), which is exactly as available, and exactly as it was, whenever replay asks again. Asset Foundation defines each class's accounting-relevant behavior (unit semantics, fractional rules, settlement vocabulary); Ledger & Accounting *enforces* it — describer and enforcer, never merged. And the domain never writes a ledger event, including for the structural events it interprets: a split's rescaling enters through the ingestion gate as a proposal, or it does not enter (§4.4).

### 4.3 Connectivity & Ingestion

*Direction: Connectivity & Ingestion depends on Asset Foundation. The two meet at the identity gate inside the ingestion gate.*

Connectivity & Ingestion owns the doors, the dialects, and the proposal pipeline; Asset Foundation owns the verdict. Every inbound fact is resolved to identity at the door, decisively or not at all (Law 6): decisive evidence resolves silently, ambiguity is surfaced for adjudication, and nothing enters the ledger with an unresolved or guessed identity — an ambiguous identity claim quarantines the *fact*, not just the name. Confirmed resolutions are recorded once and reused forever, so the same string resolves the same way through every future door. The boundary rule that keeps both domains honest: **adapters never resolve, and the Registry never parses.** An adapter that maps symbols itself holds a private identity opinion (§7.5); a Registry that reads file formats has swallowed the boundary it exists to stand behind.

### 4.4 The structural-event crossing

Structural events are the one place Asset Foundation's work has consequences in two other authorities, so the crossing gets its own contract:

1. **Announcements arrive as claims** through Connectivity & Ingestion and Market Intelligence — witnesses, zero authority.
2. **Asset Foundation adjudicates**: classifies the event into a family, determines which identities it touches, records the identity consequences it is itself authoritative over (statuses, relationships, evidence-file updates), and computes the ledger consequences the event *implies*.
3. **Implied ledger consequences leave as proposals** through the ingestion gate — attributed per portfolio, provenance-tagged with the announcement and adjudication that produced them, subject to the same admission discipline as any imported fact. The domain never holds a privileged pen.
4. **Both-or-neither.** A structural event's identity facts and ledger proposals are released as one decision. A spin-off that created a child identity but proposed no position event — or vice versa — is corruption, not progress; the consistency guarantee is owned here, at the point of interpretation, because it cannot be assembled downstream.

### 4.5 Portfolio Intelligence

*Direction: Portfolio Intelligence depends on Asset Foundation, read-only.*

It consumes classification as dated facts — exposure over a past period uses the taxonomy as it stood then — and traverses the relationship graph for analytics views ("one company" across dual listings is an on-demand aggregation over a *same-entity* edge, never a merge of records). Two prohibitions: Portfolio Intelligence never re-classifies (a private sector map beside the canonical taxonomy is a second implementation of an owned rule — Law 9), and never treats a relationship as an accounting instruction.

### 4.6 Decision Intelligence

*Direction: Decision Intelligence depends on Asset Foundation, read-only.*

It consumes definitions and capabilities to reason about what actions are *possible* (tradable, fractional, lot-constrained), and classification facts to evaluate universe and policy constraints (market membership, wrapper qualification, income character). The line, stated once in [ASSET_REGISTRY.md](ASSET_REGISTRY.md) §8 and constitutional here: **the Registry describes; policy judges.** Asset Foundation never carries a judgment-flavored fact — no "investable" flag, no quality tier, no recommendation-relevant opinion. The day a describing field encodes a judgment, the judgment has escaped its domain and its evaluation discipline with it.

*(Trust & Evaluation and Experience Platform read the domain like everything else — grades reference permanent identities; presentation looks up display symbols at render time. Neither needs a special contract; that they need none is the design working.)*

---

## 5. The Conceptual Model

Nine concepts, and the relations among them, are the entire domain. Everything in §3's subdomains is machinery for keeping these nine honest.

```
                       DEFINITION  (per class — the behavior contract)
                            │ instantiated by · grants CAPABILITIES
                            ▼
 EVIDENCE ──adjudication──▶ ASSET ◀──dated facts──  CLASSIFICATION
 (external names,           │ │ │
  time-bounded,             │ │ └──── is in one LIFECYCLE state
  plural, weighed)          │ └────── participates in RELATIONSHIPS (typed edges to other ASSETs)
                            │
                     IDENTITY (permanent tier:
                     asset_id + canonical symbol —
                     minted once, never moves)
                            ▲
              STRUCTURAL EVENT (adjudicated fact: moves lifecycle,
              authors relationships, updates evidence —
              and only ever *proposes* ledger consequences)
```

- **Asset** — the platform's permanent answer to "what is this thing?": one identity, one definition, an evidence file, dated classifications, a lifecycle state, and a place in the relationship graph. The noun of every other domain's sentences.
- **Identity** — the permanent tier: an opaque `asset_id` and a canonical symbol, minted once at verification and never reassigned, reused, or destroyed. Identity is *minted, not derived* — it never depended on any external identifier existing, which is why the model fits assets that have none.
- **Evidence** — every external name the world uses for the asset: ISINs, tickers, provider symbols, broker codes. Owned by others, mutable, plural, **time-bounded** (a recycled ticker means different things in different years, and the mapping records when it meant what), weighed at adjudication, retained forever after providers vanish. Evidence maps *into* identity; the arrow never reverses.
- **Definition** — the behavior contract of an asset *class* (§6): what kind of thing this is, declared in the platform's closed vocabulary. An asset instantiates exactly one definition; a definition constrains what its assets can claim.
- **Capability** — one queryable behavior fact granted by a definition (supports NAV pricing, supports coupons, supports corporate actions…), independently combinable, the flags engines branch on *instead of* types. Capabilities are the projection of definitions that crosses the engine boundary; per-asset facts (lot size, fractional support) may refine a definition's defaults, never contradict its vocabulary.
- **Classification** — a dated, provenance-tagged descriptive fact on a permanent identity: sector, region, currency, wrapper qualification. Mutable *on the record* — history retained — where identity is not mutable at all.
- **Lifecycle** — the state of a thing's existence, in two regimes separated by the minting moment: claim states before identity (reversible, scarless), asset statuses after (dated facts on an identity that never dies). "Delisted" changes what may happen next, never what happened.
- **Structural Event** — an adjudicated fact about what the world did to an instrument, classified into a closed family vocabulary before any consequence is formulated. The one concept that touches all the others: it moves lifecycle, authors relationships, updates evidence — and proposes, never performs, everything outside the domain.
- **Relationship** — a typed edge between two identities, carrying the sameness that identities deliberately don't. Traversable by analytics, invisible to accounting.

The load-bearing relation in the model is the vertical one: **Definition describes the class; Asset instantiates it; Capability is what engines see.** Everything to the sides — evidence, classification, lifecycle, relationships, events — is dated fact accumulating around a permanent center that never moves.

---

## 6. What an Asset Definition Is

The milestone brief asks whether definitions are metadata, behavior descriptions, plugins, contracts, or something else. The answer: **a definition is a declarative behavior contract, written in a closed vocabulary the platform owns.** Each rejected alternative clarifies one word of that sentence.

**Not metadata.** Metadata is inert — informative to whoever reads it, ignorable by whoever doesn't. Definitions are load-bearing: the Accounting Engine validates quantities against them, the ledger admits flow types because of them, valuation cadence follows from them. A fact that engines must obey is not metadata, and filing it as metadata invites the fatal casualness — an engine "helpfully" defaulting when the metadata is absent. (Genuine metadata still exists — a fund's expense ratio, a property's address — and stays in the open per-class bundle, invisible to the accounting core. The boundary test is unchanged from [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md) §2: if no engine must branch on it, it is metadata.)

**Not plugins — the slogan survives; the mechanism is rejected.** "Assets are plugins" is constitutionally enshrined (§6.1, GLOSSARY) and *economically* exact: a new class arrives by addition, engines untouched. But taken as a mechanism — executable, class-supplied code the engines load — it would be triply unconstitutional: class-specific logic is edge knowledge running inside the core (Law 10); each plugin computing its own accounting is a second implementation per class (Law 9); and code arriving with data breaks the determinism audit (Law 4), because replaying last year requires knowing which plugin *version* answered then. The platform's one prior brush with this — vendor symbol logic scattered at call sites — is the small-scale preview of what executable definitions would be at full scale.

**Behavior descriptions, but with teeth — which is what "contract" adds.** A description says what an asset class is like. A contract binds *both* sides: the definition promises to declare only things the vocabulary can express, and the engines promise that every vocabulary term has exactly one implementation that honors it. This mutual obligation is what makes the extension strategy real rather than aspirational: **a definition can only say things engines already know how to hear.** When a genuinely new class needs a word the vocabulary lacks — options need exercise semantics, futures need contract series — the response is a *governed vocabulary extension*: the new term is argued openly, added once, implemented once by the owning engine, and every existing definition is untouched. What is never the response: a branch in an engine, a special case in an adapter, a plugin. The vocabulary is the constitution's "act of description, not act of surgery" made into a concrete mechanism — and the vocabulary itself is the one thing in this domain that changes by deliberation rather than by data.

Three properties follow, and they are the design:

1. **Declarative.** A definition contains no logic — only declarations in the closed vocabulary. It can be diffed, audited, replayed against, and understood without executing anything.
2. **Interpreted by single implementations.** Engines interpret declarations through the one owner of each rule. The definition says *supports coupons*; exactly one implementation knows what admitting a coupon flow means.
3. **Closed but extensible by governance.** The vocabulary is platform-owned and versioned by deliberation. Openness lives at the *registry* of definitions (anyone may describe a new class in existing vocabulary); discipline lives at the vocabulary itself.

---

## 7. Architectural Risks

Each risk below is real — most have already drawn blood on this platform — and each prevention is structural rather than procedural: the design makes the failure hard, not merely forbidden.

### 7.1 Duplicated identity

*The same instrument arrives through two doors and becomes two assets; a holding double-counts; analytics silently disagree with accounting.* Prevention: exactly one minting path — every claim, from every door, passes candidate matching against current *and historical* mappings before minting is considered; discovery never mints; search never mints; import never mints. When duplication is discovered late, the repair is an explicit, dated, adjudicated merge — never a silent cleanup, because both identities may already be load-bearing in ledgers. Audit: two assets sharing an external identifier is a standing finding, surfaced loudly.

### 7.2 Provider coupling

*A vendor's namespace becomes platform semantics; its symbol conventions leak inward; its disappearance orphans records.* Prevention: the two-tier identity model — no external identifier, ISIN included, is ever promoted to identity; provider symbols are time-bounded mappings in an evidence file that survives the provider. The falsifiable test, inherited from the constitution's goals: **a provider's disappearance is an identity non-event.** If retiring a vendor requires touching anything below the adapter, the boundary has already failed.

### 7.3 Asset-class logic leaking into engines

*An `if asset_type == …` branch appears in an engine; each new class multiplies branches; the multi-asset era arrives as surgery.* Prevention: the definition contract (§6) plus the capability model — engines ask "does this asset support X?", never "what is this asset?". The audit is mechanical: no engine can tell what any asset is *called* or what *class* it is; a class-name string below the boundary is a defect regardless of whether it currently misbehaves. The constitutional test (§9): a new asset class whose diff touches an engine is, by that fact alone, wrong.

### 7.4 Lifecycle ambiguity

*"Deleted" assets referenced by immutable ledgers; unclear whether a suspended asset can be valued; merge semantics improvised per incident.* Prevention: a closed state vocabulary with a bright line at minting — before it, claims that can vanish scarlessly; after it, statuses on identities that never die. Every status answers the operational questions explicitly (tradable? valuable? referenceable?), and no engine ever needs to know *why* a status changed. Delisted-but-held is a position, not an anomaly; Archived is a statement about activity, never existence.

### 7.5 Registry fragmentation

*A convenience cache of symbol mappings in an adapter; a watchlist keeping its own asset table; a search feature minting on miss — each a private identity opinion that will eventually disagree with the Registry's, and the disagreement will surface as money.* Prevention: one authority by law — no domain, engine, adapter, or feature holds a private identity mapping; resolution verdicts are recorded once, centrally, and reused. The platform has already fought this fight once (the watchlist and classification consolidations); the scar is now constitutional. Discovery reads, adjudication decides, nothing else exists.

### 7.6 Definition vocabulary sprawl

*Capabilities multiply per class — `supports_thai_esg_lockup`, `supports_us_stock_dividends` — until definitions are type branches wearing contract clothing.* Prevention: vocabulary extension is governed, not free (§6); each proposed term must pass the test "does an engine need to *behave differently* because of this?" — if only analytics or presentation cares, it is metadata or classification, not capability. The vocabulary's smallness is a feature under deliberate protection; its growth rate is a health metric of the whole abstraction.

### 7.7 Structural-event authority creep

*The corporate-action machinery, needing consistency across two authorities, acquires a privileged pen: it starts writing registry facts and ledger events directly, becoming a shadow authority that bypasses both gates.* Prevention: the crossing contract (§4.4) — interpretation is authoritative, consequences are proposals, both-or-neither is released as one decision *into* the gates, never around them. The domain computes what the events should be; the admission pipeline decides that they enter; the human owns anything irreversible. No expedited lane exists, however certain the event looks.

### 7.8 Classification opinion creep

*Descriptive taxonomy quietly acquires judgment: an "investable" flag, a quality tier, a risk bucket — and suddenly the root domain is making recommendations that no evaluation layer grades.* Prevention: the describe/judge line as charter law (§2, §4.6). Classification dimensions state facts with provenance (market membership, wrapper qualification, income character); anything that ranks, scores, or recommends belongs above, where Decision Intelligence's discipline and Trust & Evaluation's grading apply. A fact no witness could testify to is an opinion, and opinions are not classifications.

---

## 8. The M6 Charter

M6 builds the **institution and its vocabulary for the assets the platform already holds** — equities and cash. It does not add asset classes, does not open ingestion doors, and does not process quantitative corporate actions end-to-end. Those are Phase 5's eras, and M6's test is that they will arrive as description, not surgery.

### Core Foundation — in M6

1. **Registry-native integration.** The authority made real: ledger references, replay, optimizer internals, and analytics keyed to permanent identity end-to-end, with symbols surviving only at the resolution boundary and the presentation surface. This completes the consolidation the Asset Registry milestone began and is M6's highest-leverage item — every other capability in this charter assumes it.
2. **The definition contract, v1.** The closed vocabulary (capabilities, unit semantics, flow types, lifecycle vocabulary) and the two definitions the platform already needs: *equity* and *cash*. Deliberately two, and deliberately unglamorous — v1 proves the mechanism (engines consuming declarations through single implementations) on classes whose behavior is already hardened, so that Phase 5's classes are pure additions. Includes the metadata/capability boundary test and the vocabulary-extension governance path.
3. **Classification as dated facts.** The consolidated taxonomy carried to its constitutional form: classifications recorded as dated, provenance-tagged facts with history retained, so analytics can ask "as of when?" — the discipline Phase 3's attribution analytics (sector timelines) will consume.
4. **Lifecycle, v1.** The claim states, the asset statuses, the minting moment — plus the structural events that require no ledger consequences: **rename** (evidence-file update, identity untouched), **suspension**, and **delisting** (status transitions). These are the events the platform's current asset universe actually experiences, and they exercise the whole lifecycle machinery without opening the ledger-consequence crossing.
5. **Relationship vocabulary, v1.** Three kinds, each already demanded by lived reality: *wraps* (the DR scar), *same-entity* (dual listings), *successor-of* (renames and conversions that end one identity in another). Recorded, dated, traversable by analytics — the graph's mechanics proven small.
6. **Catalog & Discovery, v1.** Asset search over the domain's own recorded facts — identity, classification, lifecycle — as a pure read surface. Ranking and findability, minting never.

### Future Extensions — explicitly not M6

- **Quantitative structural events end-to-end.** Splits, mergers, spin-offs with ledger consequences require the admission pipeline — attributed proposals, review, both-or-neither release — which is Connectivity & Ingestion's Phase 5 machinery. M6 records the *families and the interpretation discipline*; the crossing opens when the gate it crosses exists.
- **New asset-class definitions.** ETFs, funds, gold, crypto, property, multi-currency cash — each one definition, written in the v1 vocabulary, arriving with Phase 5. If any of them needs an engine change, M6's contract has failed and the *contract* gets fixed.
- **Entitlements and holder decisions.** Rights offerings introduce awaiting-decision states — deferred until a real asset class demands them.
- **Derivative coordinates and series.** Options (underlying + strike + expiry as identity coordinates, *derivative-of* edges) and futures (contract series) — the relationship vocabulary reserves the kinds; nothing builds until the classes arrive.
- **Automated announcement feeds.** Corporate-action witnesses at scale are Phase 5 ingestion doors; M6's structural events arrive through the doors that exist today.

The charter's shape is deliberate: **M6 makes Asset Foundation an institution — one authority, one vocabulary, one graph — sized exactly to the platform's present, and extensible by description into its future.** Every future extension above lands as new words in existing vocabularies. That is the claim the constitution makes for the whole platform (§9), owed first and most concretely by its root domain.

---

## 9. Governance

- This document is a **level-2 Domain Constitution** under [platform_architecture.md](platform_architecture.md) §11: supreme inside Asset Foundation's boundary, subordinate to the Platform Architecture at it. Ratification follows the constitutional process (§10), recorded in [DECISION_LOG.md](../engineering/DECISION_LOG.md).
- [ASSET_REGISTRY.md](ASSET_REGISTRY.md), [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md), and [CORPORATE_ACTION_DOMAIN.md](CORPORATE_ACTION_DOMAIN.md) are the domain's **level-4 technical designs**: they refine this document and are bound by it (rule G2). One alignment note is recorded rather than hidden: CORPORATE_ACTION_DOMAIN.md's self-description as a standalone "bridge domain" is superseded by §3's homing of structural-event interpretation inside Asset Foundation; its interior discipline is unchanged and remains binding at level 4.
- Vocabulary introduced here (*definition contract*, *capability*, *evidence file*, *structural event*, *claim*) is registered in [GLOSSARY.md](../GLOSSARY.md) per constitution rule V2.

## Related Documents

- [platform_architecture.md](platform_architecture.md) — the constitution; §6.1 defines this domain's boundary
- [ASSET_REGISTRY.md](ASSET_REGISTRY.md) — identity, resolution, lifecycle, classification: the institution's interior law
- [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md) — the universal model and capability vocabulary
- [CORPORATE_ACTION_DOMAIN.md](CORPORATE_ACTION_DOMAIN.md) — structural-event interpretation, validation, and lifecycle
- [ROADMAP.md](ROADMAP.md) — Phase 3, where M6 lives; Phase 5, where the extensions land
- [../GLOSSARY.md](../GLOSSARY.md) — the canonical vocabulary
