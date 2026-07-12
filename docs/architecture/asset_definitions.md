# Asset Definitions

_The subdomain constitution of Asset Definitions — how the platform describes what an asset **is**, so that no engine ever learns what any asset is called. The constitutional blueprint for every asset class the platform will ever support, and the architectural charter for Phase 3 M7._

_**Status: draft, pending ratification.** Upon ratification this document carries the authority of [asset_foundation.md](asset_foundation.md) (the level-2 Domain Constitution) inside the Definitions subdomain it charters (asset_foundation.md §3.2): it refines §§5–6 of that constitution and is bound by it everywhere they touch. It binds [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md) §§2, 5, 9–11 as level-4 technical design (constitution rule G2). It designs the domain, not the implementation: no schemas, no code, no APIs, no storage formats._

---

## 1. Purpose

Asset Foundation answers one question for the whole platform: *what is this thing?* The Identity subdomain answers it for **instances** — this listing, this contract, this house — permanently and unambiguously. The Definitions subdomain answers it for **kinds**: what can anything of this kind do, what may be done to it, and how must the platform's machinery treat it — stated once per kind, in a language every engine already speaks.

The question this subdomain exists to dissolve is the central tension of the multi-asset era: **how does a platform serve every asset class without any engine knowing any asset class?** The constitution's answer ([platform_architecture.md](platform_architecture.md) §9) is that a new class arrives as *an act of description, not an act of surgery*. This document is where that act is defined: what a description is, what it may say, who hears it, and how the language it is written in grows.

The stakes are stated plainly, because they discipline everything below. Every failure the multi-asset transition can suffer — an `if asset_type == …` branch in an engine, a plugin that computes its own accounting, a vocabulary that balloons into type-checking by another name, two definitions for one behavior — is a failure of *this subdomain's* discipline. The engines are the treasure (constitution §2.3); definitions are the mechanism by which the treasure is multiplied instead of spent. If M7 is done rightly, Phase 5's asset classes are boring: one new document each, zero engine diffs, forever.

---

## 2. Design Philosophy

### 2.1 A contract between parties who never meet

A definition is written by someone the engines will never know — the person who, years from now, describes the platform's first bond, first option, first rental property. The engines were built by someone that describer will never meet. The **vocabulary** is the treaty between them: the definition promises to declare only things the vocabulary can express, and the platform promises that every word of the vocabulary is honored by exactly one implementation that already exists. *A definition can only say things engines already know how to hear* ([asset_foundation.md](asset_foundation.md) §6) — and, reciprocally, everything the vocabulary can say, some engine has exactly one way of honoring. Neither party can surprise the other. That mutual unsurprisability is the entire economics of extension-by-description.

### 2.2 Kinds are individuated by behavior, not by name

"ETF," "mutual fund," "REIT" are the world's marketing categories. The definition system does not care what the world calls a kind of thing — it cares what the kind *does*: how it is counted, how it trades, what flows it generates, what the world can do to it. Two names with identical behavior contracts are **one definition**, distinguished downstream by classification. One name spanning two genuinely different behavior contracts is **two definitions**, whatever the brochure says. This single principle is the structural defense against duplicated definitions (§10.4): a new definition earns its existence only by demonstrating a behavioral difference no existing definition expresses.

### 2.3 Closed language, open library

The platform's identity discipline is *minted, not derived*; the definition discipline is the same posture applied to language: **deliberated, not accumulated.** The vocabulary is closed, platform-owned, and extended only by governance — never by data, never by a provider's category list, never by the convenience of the class being onboarded this week. Openness lives one level up, at the **library**: anyone may describe a new kind in the existing words, and describing one is deliberately cheap. Discipline at the vocabulary, freedom at the library — invert either and the design fails (a free vocabulary is type-branching wearing contract clothing; a closed library is a platform that cannot grow).

### 2.4 Two readers, one text

A definition has exactly two consumers, and serving both with one artifact is the design. **Engines** consume it at run time as queryable declarations — presence-tested, never interpreted. **Humans** consume it at governance time as a reviewable document — diffable, arguable, comparable against its siblings. This is not a convenience; it is the point: on this platform, *what an asset class is* is a reviewable text with a change history, not an emergent property of scattered code paths. When the platform's understanding of a kind is wrong, the error is visible in a paragraph, not archaeologically reconstructed from branches.

### 2.5 Description ends where opinion begins

A definition states what is *possible* for a kind — never what is *advisable* about it. The describe/judge line that governs the whole root domain ([asset_foundation.md](asset_foundation.md) §4.6) crosses through this subdomain with special force, because definitions are the facts engines obey without appeal: an opinion smuggled into a definition becomes an opinion enforced as arithmetic, exempt from the evaluation discipline every judgment owes. No definition ever carries investability, quality, riskiness, or suitability. Definitions describe; policy judges; Trust & Evaluation grades the judges.

---

## 3. Constitutional Laws

Binding inside the Definitions subdomain. A change that violates one is wrong by definition; deliberately breaking one requires amending this document first, recorded in [DECISION_LOG.md](../engineering/DECISION_LOG.md).

**D1 — One kind, one definition; one asset, exactly one definition.**
Every asset instantiates exactly one definition. Definitions are individuated by behavior, never by name: identical declarations are one definition, however many things the world calls them.

**D2 — Definitions declare; they never execute.**
A definition contains no logic, no code, no formula, and references none. It is a set of declarations in the closed vocabulary — diffable, auditable, and replayable-against without executing anything. "Assets are plugins" is an economics, never a mechanism.

**D3 — The vocabulary is closed and platform-owned.**
A definition can only say things engines already know how to hear. Every word exists because some engine must *behave differently* on account of it; a word only analytics or presentation cares about is classification or metadata, not vocabulary.

**D4 — One word, one implementation.**
Every vocabulary term is honored by exactly one implementation in exactly one owning engine (Law 9 applied to language). The word's meaning *is* its owner's contract; no second engine ever reinterprets it.

**D5 — Engines consume declarations, never kinds.**
No engine may hold, branch on, or even receive a class name. The audit is mechanical: no engine below the boundary can tell what any asset is called or what kind it is. A class-name string in an engine is a defect regardless of whether it currently misbehaves.

**D6 — The capability plane is flat.**
No hierarchy, no inheritance, no implication, no "base definition." Everything true of a kind is declared explicitly in its definition; nothing is inferred from another word, another definition, or a family resemblance.

**D7 — Absence is a declaration.**
An ungranted capability means *does not support* — never "unknown," never "probably." Engines refuse the unsupported operation loudly; they never default, compensate, or guess around an absence.

**D8 — Definitions bind forward, never backward.**
A published definition version is immutable. A recorded fact replays under the definition that admitted it; no definition change ever re-validates, re-interprets, or re-books history. Determinism (Law 4) reaches this subdomain as: *the definition consulted is part of the recorded state.*

**D9 — The definition binding is as permanent as identity.**
An asset's definition is fixed at minting. When the world changes what a thing is — a fund restructures, a share class converts — that is a structural event and, in general, a successor identity; never an in-place redefinition. Repairing a *mis-definition* is an explicit, dated, adjudicated act, like a merge — never a silent correction, because the binding may already be load-bearing in ledgers.

**D10 — Instance facts refine; they never contradict.**
Per-asset facts (lot size, native currency, venue, fractional allowance) specialize within what the definition permits. An instance fact that contradicts its definition's vocabulary is a registration-time defect, surfaced loudly — never a runtime negotiation.

**D11 — Definitions describe possibility, never judgment.**
No investable flag, no quality tier, no risk bucket, no recommendation-relevant opinion — ever. The day a definition field encodes a judgment, the judgment has escaped its domain and its grading discipline with it.

**D12 — Metadata is invisible to engines.**
The open per-kind metadata bundle exists for analytics, presentation, and human context. The moment an engine branches on metadata, one of two things is true: the vocabulary is missing a word (and the governed extension path is the response), or the engine has committed a defect (and the branch is removed). The branch itself is never the answer.

---

## 4. Domain Responsibilities

### What Definitions owns

- **The vocabulary.** The closed set of words definitions are written in — the declaration axes (§5.1), the grant terms, and the rules by which the set grows (§8). The vocabulary is the one thing in Asset Foundation that changes by deliberation rather than by data.
- **The library.** The registry of definitions themselves: each kind's complete declaration, its version history, and the guarantee that the library contains no two definitions with identical behavior (D1).
- **The binding discipline.** That every asset is bound to exactly one definition at minting, that the binding is permanent (D9), and that instance facts recorded against the asset stay within what its definition permits (D10).
- **The projection.** The capability view engines actually consume — the queryable form of each definition that crosses the engine boundary, and the promise that it says nothing the definition doesn't.
- **The boundary test.** The adjudication of every "where does this fact live?" question: vocabulary vs. classification vs. metadata vs. instance fact. The test is stated once (§5.3) and owned here, so it is applied consistently instead of re-argued per feature.
- **The extension path.** The governed process by which a genuinely new word enters the vocabulary (§8) — argued openly, added once, implemented once, recorded.

### What Definitions never owns

- **The implementations.** Every vocabulary word is honored by its owning engine (D4). Definitions say *supports coupons*; exactly one accounting implementation knows what admitting a coupon flow means. A definitions subdomain that computes has become a plugin system.
- **Instance identity and instance facts.** The asset, its `asset_id`, its evidence file, its per-asset refinements belong to the Identity subdomain and the asset record. Definitions describe the kind; they hold no roster of members.
- **Classification.** Sector, region, market membership, wrapper qualification — dated, curatorial, instance-level facts, stewarded next door (asset_foundation.md §3.3). A definition never contains a jurisdiction, a market, or a tax wrapper's name (§7.2).
- **Worth and liquidity.** Prices, spreads, depth, tradedness — observations, owned by Market Intelligence. A definition says *how* a kind is valued and traded, never *what it is worth* or *how easily, today* (§5.3).
- **What happened.** Flows, holdings, and their history are Ledger & Accounting's. A definition says a coupon is *admissible*; whether one occurred is forever the ledger's fact.
- **Lifecycle positions.** The Lifecycle subdomain owns the state vocabulary and every instance's position in it. A definition declares which lifecycle *pattern* a kind follows (open-ended, scheduled-terminal); it never knows where any instance stands.
- **Judgment and tax rules.** Suitability is Decision Intelligence's; taxation is a function of jurisdiction, wrapper, and person — none of which a kind possesses (§5.3).

---

## 5. Conceptual Model

### 5.1 The anatomy of a definition: seven axes

A definition is the complete set of a kind's declarations along a small, closed set of **axes** — the seven questions every engine, present or future, asks about anything it is handed. The axes are constitutional; the words available on each axis are the canonical vocabulary (§7); the specific declarations are the individual definition.

1. **Unit semantics** — *how is it counted?* What one unit is (a share, a gram, a currency minor unit, a contract), whether quantity is discrete or continuous, whether it may be negative, and what conservation means for it. The axis the Accounting Engine can never do without.
2. **Acquisition semantics** — *how does it change hands?* The mechanism by which instances are acquired and disposed: venue-traded, NAV-window subscription/redemption, negotiated private transfer, or not transactable at all. The mechanism, never the venue — venues are instance facts.
3. **Settlement semantics** — *when is a change of hands real?* Which settlement pattern the kind follows: cycle-based, instant, negotiated/manual. The actual cycle length of a given listing is an instance fact refining this declaration (D10).
4. **Valuation semantics** — *what may it be asked to be worth, and when?* Which valuation question Market Intelligence can meaningfully be asked about instances: continuous quotation, periodic NAV, appraisal-on-event, or identity (cash is worth its face amount). Cadence and question-shape only — never a price, never valuation mathematics.
5. **Flow grants** — *what does holding it generate?* Which holding-generated flow types are admissible against instances — dividend, coupon, interest, rent, staking reward, distribution — each carrying its income character. A flow the definition does not grant is a flow the ledger refuses (D7).
6. **Event-family grants** — *what can the world do to it?* Which structural-event families ([asset_foundation.md](asset_foundation.md) §3.4) instances can undergo: split, merger, spin-off, redemption, expiry, exercise. Grants only — interpretation of actual events stays in Lifecycle & Structural Events.
7. **Existence pattern** — *how does its story end, and what must it be connected to?* The lifecycle pattern the kind follows (open-ended; scheduled-terminal like a bond's maturity or an option's expiry) drawn from Lifecycle's vocabulary, and the relationship kinds instances may or **must** participate in (a derivative must carry a *derivative-of* edge to an underlying; the edge itself is the Relationships subdomain's).

Nothing else. A fact that fits no axis is, by that failure, not a definitional fact: it is classification, metadata, an instance fact, or an observation — and the boundary test (§5.3) says which. Adding an eighth axis is possible but constitutional: it amends this document, because it asserts there is a question about kinds that every engine can ask which the platform had not yet named.

### 5.2 What a definition is not

Six neighboring concepts, each sharing a border with definitions, each border bright:

**Not the Asset.** The asset is the instance — one permanent identity, one evidence file, one lifecycle position. The definition is the kind, instantiated by many assets and surviving all of them. An asset without a definition is unregisterable; a definition without assets is merely unused. The asset answers *which thing*; the definition answers *what kind of thing*.

**Not metadata.** Metadata is inert — informative to whoever reads it, ignorable by whoever doesn't, invisible to engines by law (D12). Definitions are load-bearing: engines *obey* them. The boundary test is behavioral, not importance-based: a bond's coupon *rate* matters enormously and is metadata (no engine branches on it — the ledger records the coupon that actually arrived); that bonds *pay coupons at all* is a definitional flow grant (the ledger admits the flow type because of it).

**Not classification.** Classification is curatorial: dated, provenance-tagged, instance-level facts that legitimately change — a company is re-sectored, a fund is re-domiciled, a market is reclassified. Definitions are constitutional: kind-level contracts that change only by deliberation and never retroactively (D8). Classification places an asset *among others*; a definition states what any asset of the kind *can do*. A sector change is weather; a definition change is a constitutional event. The two must never trade content: a classification that engines branch on has become a smuggled definition; a definitional word naming a jurisdiction has become a smuggled classification (§7.2).

**Not the Capability.** A capability is one queryable declaration; the definition is the complete set — the words versus the sentence. Capabilities are the *projection* of definitions that crosses the engine boundary: engines see grants and semantics; only governance ever reads the definition whole.

**Not Lifecycle.** Lifecycle is the state of one instance's existence — active, suspended, delisted, matured. The definition declares which existence *pattern* the kind follows and therefore which states are reachable; it never tracks, moves, or knows any instance's position. "Bonds mature" is definitional; "this bond matures 2031-03-15" is an instance fact; "this bond has matured" is a lifecycle status.

**Not Relationships.** Relationships are recorded edges between specific identities. A definition declares *participation rules* — which edge kinds instances of this kind may or must carry — and nothing more. "An option must have an underlying" is definitional; "*this* contract's underlying is *that* listing" is the Relationships subdomain's recorded fact.

### 5.3 Every candidate challenged

The milestone brief proposes a list of contents. Each is admitted, split, or rejected — and the verdicts are the boundary test in action:

| Candidate | Verdict | Where it lives |
|---|---|---|
| Valuation model | **Split.** The *question-shape and cadence* (axis 4) is definitional. The mathematics of valuation, the models, and every price are Market Intelligence's. | Axis 4 · Market Intelligence |
| Ownership model | **Admitted, renamed.** "Ownership model" dissolves into unit semantics: what one unit is, divisibility, sign, conservation. | Axis 1 |
| Tradability | **Split three ways.** The *mechanism* (axis 2) is definitional. Whether *this instance* may trade *today* is lifecycle status. Lot sizes and venue constraints are instance facts. | Axis 2 · Lifecycle · instance facts |
| Settlement | **Split.** The settlement *pattern* is definitional; the actual cycle of a listing is an instance fact refining it. | Axis 3 · instance facts |
| Income behaviour | **Admitted.** Flow grants with income character — the definitional fact the ledger's admission discipline consumes. | Axis 5 |
| Taxation characteristics | **Rejected, almost entirely.** Tax is a function of *(flow character × jurisdiction × wrapper × person)*. Only flow character is a property of the kind, and axis 5 already carries it. Jurisdiction and wrapper qualification are classification; the person is Wealth Intelligence's. A definition carrying a tax rule breaks for the first user in a second country — the proof it never belonged to the kind. | Axis 5 (character only) · Classification · Wealth Intelligence |
| Corporate action support | **Admitted.** Event-family grants — which families *can* happen; never the interpretation of any actual event. | Axis 6 |
| Liquidity | **Rejected.** Liquidity is weather, not climate: an observation about markets on a day, owned by Market Intelligence. The only definitional residue is the trading mechanism, already axis 2. A "liquid/illiquid" word in the vocabulary would be an opinion with a timestamp problem. | Market Intelligence |
| Pricing model | **Rejected as distinct.** Same verdict as valuation model. And sharper: a *payoff formula* is not a definition fact — an option's definition grants exercise and mandates an underlying; it never encodes Black-Scholes, intrinsic value, or any arithmetic (D2). | Axis 4 · Market Intelligence |

The pattern in the verdicts is the subdomain's whole epistemology: **a definitional fact is a fact about the kind that some engine must behave differently on.** Facts about instances refine; facts about markets are observed; facts about jurisdictions are classified; facts about persons are Wealth Intelligence's; opinions are nobody's to define.

---

## 6. The Capability System

### 6.1 What a capability is

A capability is **one queryable declaration granted by a definition** — the unit of the treaty of §2.1: a single word both sides have agreed on, backed by exactly one implementation (D4). Capabilities come in two shapes, both closed, both queryable, both constitutionally identical:

- **Grants** — boolean declarations: *supports coupons*, *supports corporate actions*, *supports fractional trading*. Present or absent, and absence is itself a declaration (D7).
- **Semantics** — valued declarations along a closed axis: unit semantics is *discrete* or *continuous*; valuation cadence is *continuous quote* or *periodic NAV* or *appraisal*. Not boolean, but drawn from an enumerated, platform-owned set of values — never free text, never open-ended.

What crosses the engine boundary is exactly this projection and nothing else: grants and semantics, keyed to the asset in hand. Engines never receive the definition as a document, never receive the kind's name, never receive metadata.

### 6.2 Are capabilities hierarchical? No — and constitutionally no.

Hierarchy is inheritance, and inheritance was already tried and rejected at the model level ([UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md) §5): a lineage forces every kind into one ancestry and makes multi-behavior kinds — a listing with both market quotes and fund NAV — awkward or impossible. The subtler danger is worse than the awkwardness: a hierarchy invites an **implication engine** ("intraday implies daily," "coupon-bearing implies income-bearing"), and every implication rule is a second, hidden place where truth about a kind is manufactured — truth no definition declared and no diff will show. The flatness law (D6) forbids all of it: if two things are true of a kind, its definition declares both, explicitly, even when one "obviously" follows from the other. Obviousness is not a declaration. The cost is a few redundant-looking grants per definition; the purchase is that the complete truth about every kind is *written down in exactly one place*.

For the same reason there is no "base definition," no "abstract equity-like template," no definition that exists to be extended. Every definition is complete and freestanding. Reuse happens in the *authoring* (the person writing the bond definition reads the equity definition), never in the *semantics* (nothing at run time resolves one definition through another).

### 6.3 Do capabilities compose? As sets — never as algebra.

A definition is a set of capabilities; sets combine by union at authoring time and are queried by membership at run time. That is the entirety of composition. What is deliberately absent:

- **No composite words.** No umbrella capability ("supports income") standing for a disjunction of real ones. An engine that needs "any income flow" asks about the flows it actually implements, by name. Umbrella words rot: the day a new income flow is added, every umbrella silently changes meaning without any definition changing text — semantic drift by construction (§10.5).
- **No capability arithmetic.** No rules of the form "A + B ⇒ C." Conjunctions live in *engines* — an operation may legitimately require several capabilities at once ("venue-traded *and* fractional") — but the requirement is the engine's published contract for that operation, not a new fact about the kind.
- **Families for humans, never for engines.** The vocabulary is *organized* for governance by the three-part spine the transaction model already proved (quantity changes · holding-generated flows · costs and adjustments, [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md) §9): a proposed new word must name its family or justify a new one. But no engine ever queries a family. Families are a librarian's shelving, not a runtime fact.

### 6.4 Which capabilities are fundamental

The fundamental capabilities are the declarations without which the deterministic core cannot keep its own laws — the ones consulted to conserve NAV, admit flows, validate quantities, and replay: **unit semantics, acquisition semantics, settlement semantics, and the flow grants.** These are fundamental in the strict sense: an asset cannot be *ledgered* without them, so no definition may omit them — every definition declares all four axes, even when the declaration is an honest "not transactable" or "no flows."

The remaining axes — valuation semantics, event-family grants, existence pattern — are fundamental to the platform but not to conservation: they serve valuation, structural-event interpretation, and lifecycle, and their absence degrades meaning rather than corrupting arithmetic. The distinction matters for exactly one reason: it ranks the vocabulary's protection. A defect in a flow grant mis-books money; a defect in a valuation cadence mis-values it. Both are defects; only one is unrepairable downstream.

### 6.5 How engines reason about capabilities

Five disciplines, each the runtime shadow of a law:

1. **Ask, never identify** (D5). The only question an engine ever poses is "does this asset's definition declare X?" — never "what is this?" An engine that cannot phrase its need as a capability query has found either a missing vocabulary word or its own design error.
2. **Require, never enumerate.** An engine states which capabilities an operation requires and serves *whatever satisfies them* — including kinds invented years after the engine shipped. It never maintains a list of kinds it "knows work."
3. **Refuse, never default** (D7, Law 13). An operation against an asset lacking the required grant fails loudly, with the missing capability named. No fallback semantics, no "treat it like an equity," no silent skip.
4. **Unknown is unsupported.** A word an engine has never heard of is, to that engine, simply not granted. This is what makes vocabulary growth additive: new words extend the engines that implement them and are invisible to every engine that doesn't.
5. **Declared, never inferred** (D6). Engines take the projection as complete truth. No engine derives an undeclared capability from a declared one, from metadata, from classification, or from observed history — however suggestive.

---

## 7. Canonical Vocabulary

### 7.1 Three registers

The language of this subdomain lives in three registers, with different owners and different change disciplines:

- **Constitutional terms** — the concepts this document is built from: *definition*, *capability*, *grant*, *axis*, *flow type*, *event family*, *unit semantics*, *definition version*. Registered in [GLOSSARY.md](../GLOSSARY.md) (constitution rule V2), reserved (rule V3): changing what one *means* amends this document.
- **Canonical vocabulary** — the actual closed word lists on each axis: the flow types, the unit kinds, the settlement patterns, the valuation cadences, the event families, the grant names. Platform-owned, maintained in the definition library, every entry registered in the glossary, every addition through §8's gate. These words are the treaty language of §2.1 — small by design, and their count is a health metric of the whole abstraction.
- **Implementation spellings** — enum names, field names, storage forms. Free, level-6, invisible to this document. The vocabulary constrains what may be *said*; it never dictates how a codebase spells it.

### 7.2 The anti-explosion rules

Vocabulary sprawl is the failure mode that turns the contract back into type-branching ([asset_foundation.md](asset_foundation.md) §7.6). Four rules keep the language small, each mechanical enough to apply in review:

1. **The behavioral-difference test** (D3). A word enters only if some engine must behave differently because of it. "Analytics would like to filter on it" admits it to classification; "the UI wants to show it" admits it to metadata; neither admits it here.
2. **No proper nouns.** No jurisdiction, market, venue, vendor, wrapper, or regulation ever appears in a vocabulary word. `supports_thai_esg_lockup` is a classification fact (wrapper qualification) wearing a capability costume; the moment a word needs a country to be true, it is describing an instance's circumstances, not a kind's behavior.
3. **No synonyms, no umbrellas.** One meaning, one word (rule V1); no word whose meaning is "any of those other words" (§6.3). A proposed word that overlaps an existing one is a renaming argument, not an addition.
4. **Name the family.** Every proposed word must place itself in the vocabulary's existing organization (§6.3) or openly argue for a new family — so that growth is legible, and a fourth family is recognized as the significant event it is.

### 7.3 Which words become constitutional

Deliberately few. The **axes** (§5.1) are constitutional: they are the claim that seven questions exhaust what engines ask about kinds. The **register boundaries** (§7.1) are constitutional. The **individual words** on each axis are canonical but not constitutional: adding a flow type is governance (§8); it does not amend this document. This split is what keeps the constitution stable while the language breathes — the platform can learn a new word in a week, but a new *kind of question* is a constitutional event, as it should be.

---

## 8. Evolution Rules

### 8.1 The path for a new asset class

Every new class walks the same three-step ladder, stopping at the first step that suffices:

**Step 1 — Describe.** Attempt the class in the existing vocabulary: seven axes, existing words. If it can be said, it is done — the diff is one new definition in the library and nothing else. This is the expected case, and the design's success is measured by how often it is the actual case.

**Step 2 — Extend.** If a genuinely new word is needed, the governed extension path: state the behavioral difference (which engine must behave differently, and how); pass the anti-explosion rules (§7.2); identify the one owning engine; implement the word once, with its test corpus; register it in the glossary; record the addition in [DECISION_LOG.md](../engineering/DECISION_LOG.md). Then return to Step 1. Every existing definition is untouched — extension is additive, always.

**Step 3 — Amend.** If the class poses a question no axis expresses — not a new word, a new *kind* of question — that is a constitutional amendment to §5.1, with the full weight that carries. This step is expected to be rare to the point of memorability.

What is never a step, at any rung: a branch in an engine, a special case in an adapter, executable class-supplied behavior, a fact hidden in metadata that an engine quietly reads, or a "temporary" exception. The acceptance test for every class, inherited from the constitution (§9) and binding here: **the diff for a new asset class contains one new definition and zero engine changes.** A class that fails the test has found a defect in the vocabulary — and the vocabulary, never the engine, is what gets fixed.

### 8.2 Versioning

Definitions change the way constitutions change — rarely, explicitly, forward-only:

- **Additive within a version.** A shipped definition's declarations never shrink in place. Widening (a newly granted flow, a newly granted event family) is a new version, openly recorded.
- **Narrowing is the sharp case.** Removing a grant is also a new version, and it faces the harder question: what of the instances, and the ledgers, that relied on it? The answer is D8 — recorded history replays under the version that admitted it, always — and the narrowed version governs only what may happen *next*.
- **Versions are immutable once published** (D8). A definition version is part of the platform's recorded state: replay reads it as it stood, which is only possible if it never moves.
- **Assets bind to definitions; versions govern moments.** An asset's binding (D9) is to the definition; which *version* governed a recorded fact is determined by when the fact was admitted. Nothing ever re-decides that.

---

## 9. Examples

Each class below is stated as its walk up §8.1's ladder. Identity questions (what the evidence file looks like, how the instance is minted) are [ASSET_REGISTRY.md](ASSET_REGISTRY.md) §11's and are not restated; this is the *definitional* view only.

**Cash** — already v1, and the degenerate case that proves absence is expressive: currency-amount unit semantics, continuous quantity, instant settlement, identity valuation (worth its face amount), an interest flow grant, no event families, open-ended existence. Step 1.

**ETF** — Step 1, and the test of §2.2's individuation principle. Venue-traded, discrete units, cycle settlement, dividend/distribution flow, corporate-action families, *and* — the interesting declaration — both continuous-quote and periodic-NAV valuation semantics on one kind, which the flat capability plane expresses without ceremony. Whether ETF is truly a distinct definition or equity's contract plus a NAV grant is decided by the declarations, not the name — and either answer is a healthy outcome.

**Bond** — Step 2, twice, both words long anticipated: the *coupon* flow type (one owner: the accounting implementation that admits it), and the *scheduled-terminal* existence pattern (maturity as a known-in-advance terminal status; a call as an early one — both Lifecycle vocabulary the definition merely selects). After those two additions: pure description.

**Option** — the first genuinely new event family: *exercise/expiry*, plus a **mandatory** relationship participation (*derivative-of*, an edge kind the Relationships subdomain adds openly). Unit semantics are unremarkable (discrete contracts). What is constitutionally instructive is what the definition does **not** contain: no strike-payoff arithmetic, no moneyness, no pricing model — valuation mathematics never enters a definition (§5.3). Strike and expiry are identity coordinates, the Registry's business.

**Future** — the same coordinate pattern, one honest new word: a *variation-margin* flow character — a signed, holding-generated daily settlement flow unlike any income type — plus the *contract-series* relationship for analytics continuity. A roll is two transactions against two identities, which the definition system doesn't even notice: it was never a fact about the kind.

**Crypto** — Step 1 with one or two Step-2 words: continuous quantity, near-instant settlement, continuous quotation, the already-reserved *staking* flow. Fork and airdrop are candidate event families argued when a real position demands them — not before (§8.1 is walked by need, never speculatively).

**Property** — Step 1, mostly by honest absence: negotiated acquisition, manual settlement, appraisal valuation, *rent* flow, no event families, open-ended existence, indivisible unit semantics. The kind that would have broken an exchange-shaped model, described here without one engine noticing.

**Business (private ownership)** — property with a different flow profile: appraisal valuation, negotiated transfer, distribution flows, sparse everything else. If the platform can say "illiquid, privately transferred, appraisal-valued, distribution-paying" in existing words — and after Property it can — a private business is Step 1.

**Derivatives in general** — the reserved pattern, stated once: mandatory underlying participation, expiry-shaped existence, event families for exercise/assignment/settlement-at-expiry. Each concrete derivative class selects from this pattern by declaration. What keeps the pattern honest is D2: however exotic the payoff, the definition only ever says *that* value derives from another identity — never *how*.

The aggregate claim of the nine walks: **two or three governed words per genuinely novel class, trending to zero as the vocabulary matures — and zero engine diffs, always.**

---

## 10. Architectural Risks

Each risk is real, most have a precedent scar somewhere in the platform's history, and each prevention is structural — the design makes the failure hard, not merely forbidden.

### 10.1 Capability explosion

*Words multiply per class and per market until definitions are type branches wearing contract clothing, and "does this support X?" is just "is this a Thai equity?" with extra steps.* Prevention: the four anti-explosion rules (§7.2), applied at the only gate through which words enter (§8.1 Step 2); the behavioral-difference test as law (D3); vocabulary size published as a health metric. The deepest defense is the no-proper-nouns rule: explosion historically arrives wearing a jurisdiction's name.

### 10.2 Implicit inheritance

*A "base equity" definition appears for convenience; or an implication engine starts deriving "daily pricing" from "intraday pricing" — and truth about kinds is manufactured in a second place no diff shows.* Prevention: the flatness law (D6) — no hierarchy, no template definitions, no implication rules anywhere; every definition complete and freestanding; redundant-looking explicit grants accepted as the deliberate price. The audit: the complete truth about any kind must be readable in exactly one document.

### 10.3 Asset-specific branching

*An engine grows an `if asset_type == …` — the exact failure this subdomain exists to make impossible.* Prevention: engines never receive the kind at all (D5) — one cannot branch on what one was never handed; the five reasoning disciplines (§6.5); the mechanical audit that no class-name string exists below the boundary. The constitutional test: a new class whose diff touches an engine is, by that fact alone, wrong ([asset_foundation.md](asset_foundation.md) §7.3).

### 10.4 Duplicated definitions

*"ETF," "index fund," and "tracker" arrive through three doors as three definitions with identical declarations, and the library becomes a synonym list with governance overhead.* Prevention: individuation by behavior (D1) — a new definition must demonstrate a declaration no existing definition makes, checked at the library's single admission point; names live in classification, where plurality is legitimate. The standing audit: two definitions with identical declarations are a finding, surfaced loudly.

### 10.5 Semantic drift

*"Supports dividends" quietly means something different to the ledger than to analytics; or an umbrella word's meaning shifts when the vocabulary grows; five years on, one word is two rules.* Prevention: one word, one implementation, one owner (D4) — a word's meaning *is* its owner's contract and test corpus, so a second interpretation has no place to live; no umbrella words (§6.3); glossary registration with reserved meanings (rule V1/V3). Drift requires two homes; the design allots one.

### 10.6 Hidden plugins

*A definition "just this once" carries a formula, a script reference, a per-class hook — and code arrives with data, unversioned by deliberation, breaking the determinism audit.* Prevention: declarative-only as law (D2); the projection that crosses the boundary is structurally incapable of carrying behavior (grants and enumerated semantics only, §6.1); replay's dependence on definition versions (D8) means an executable definition would be a replay input that cannot be frozen — the violation is self-announcing.

### 10.7 The metadata backdoor

*The vocabulary gate holds, so a fact that couldn't pass it hides in the open metadata bundle — and an engine quietly reads it there. The closed vocabulary now has an open annex.* Prevention: metadata invisible to engines as law (D12), with the two-outcome rule — every engine-read of metadata is either a missing word (fix the vocabulary) or a defect (remove the read), never an accepted state. The audit is as mechanical as 10.3's: engines' inputs are the projection, full stop.

### 10.8 Retroactive redefinition

*A definition is "corrected" in place; replay of a five-year-old ledger now validates differently; determinism is lost not to a provider but to the platform's own hygiene.* Prevention: published versions immutable (D8); recorded facts replay under the version that admitted them; mis-definition repair as an explicit, dated, adjudicated act (D9) that governs the future and never re-books the past — the same discipline as an identity merge, for the same reason.

### 10.9 Judgment creep

*A "risk tier" or "investable" field lands in a definition because policy wants it enforced everywhere — and the root domain is silently making recommendations no evaluation layer grades.* Prevention: possibility-never-judgment as law (D11); the boundary test's epistemology (§5.3) — a definitional fact must be a fact *about the kind's behavior*, and no witness could testify to "attractive"; Decision Intelligence's envelope is where policy binds, in the open, graded.

---

## 11. Governance

- This document charters the **Definitions subdomain** ([asset_foundation.md](asset_foundation.md) §3.2) and carries its parent constitution's authority inside that boundary; it is subordinate to [asset_foundation.md](asset_foundation.md) at the subdomain boundary and to [platform_architecture.md](platform_architecture.md) everywhere. Ratification follows the constitutional process (constitution §10), recorded in [DECISION_LOG.md](../engineering/DECISION_LOG.md).
- [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md) §§2, 5, 9–11 are the subdomain's **level-4 technical design** and are bound by this document (rule G2). One alignment note, recorded rather than hidden: that document's capability list and universal fields are hereby organized under §5.1's seven axes; its content is unchanged, its organization is superseded.
- The laws D1–D12 refine — and never relax — constitution Laws 4, 9, 10, and the parent constitution's §6. A conflict between this document and either parent is a defect resolved upward (rule G4).
- Vocabulary introduced here (*grant*, *axis*, *flow type*, *event family*, *unit semantics*, *definition version*, *definition vocabulary*) is registered in [GLOSSARY.md](../GLOSSARY.md) per rule V2.
- The M5 Track B technical design's Asset Definition v1 mechanism ([../implementation/M5_TRACK_B_NATIVE_INTEGRATION_TDD.md](../implementation/M5_TRACK_B_NATIVE_INTEGRATION_TDD.md) §8) predates this constitution and is level-4/6; where its guarantees already match these laws (additive-only versions, unknown-is-unsupported, the vocabulary test) they are hereby ratified; anything in it this document contradicts is to be conformed, not grandfathered.

## Related Documents

- [platform_architecture.md](platform_architecture.md) — the constitution; Laws 4, 9, 10 and §9's extension test bind this document
- [asset_foundation.md](asset_foundation.md) — the parent domain constitution; §3.2 charters this subdomain, §6 states what a definition is
- [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md) — the level-4 universal model and capability list this document binds
- [ASSET_REGISTRY.md](ASSET_REGISTRY.md) — the identity authority; instance identity, evidence, and minting (the other half of "what is this thing?")
- [CORPORATE_ACTION_DOMAIN.md](CORPORATE_ACTION_DOMAIN.md) — structural-event interpretation, whose families definitions grant
- [ROADMAP.md](ROADMAP.md) — Phase 3, where M7 lives; Phase 5, where the described classes arrive
- [../GLOSSARY.md](../GLOSSARY.md) — the canonical vocabulary
