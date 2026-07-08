# Architecture Handbook

| | |
|---|---|
| **Version** | v4.0 |
| **Last Updated** | 2026-07 |
| **Documents** | 10 |

*This directory is the architectural record of the Portfolio Intelligence Platform. This README is its introduction: what the handbook is, how its documents fit together, in what order to read them, and what philosophy binds them. It organizes the existing architecture; it does not extend it.*

---

## 1. Introduction

These documents exist because the platform is expected to outlive every implementation detail it currently contains. Code changes with each phase; providers come and go; the user interface is rewritten as understanding improves. What must not change casually is the set of domain boundaries — where identity lives, where accounting truth lives, where the outside world stops and the platform begins. This handbook records those boundaries.

Architecture is documented here *before* implementation, deliberately. Each document answers a question of meaning — *what is an Asset? what is a Portfolio? who owns cash?* — so that when implementation arrives, it is filling in a shape that has already been argued for, not inventing one under deadline pressure. A boundary drawn in a document costs a page to move; a boundary drawn in a database schema costs a migration, a backfill, and a season of subtle bugs.

The platform is designed around stable domain boundaries because its history has taught it that lesson concretely. The problems that hurt most — phantom cash flows, provider symbols leaking into business logic, imported positions contaminating returns — were all boundary failures: some piece of the outside world was allowed to carry meaning inside the platform. Every document in this handbook is, at heart, a description of one boundary and the rules for crossing it.

These documents describe intent, not current code. Where the code and the handbook disagree, the handbook states where the platform is going; `ARCHITECTURE.md` in this directory describes the system as built, and `ROADMAP.md` describes when the gap closes.

---

## 2. Reading Order

Read the documents in the order below. Each one assumes the vocabulary of the ones before it.

**1. [PLATFORM_EVOLUTION.md](PLATFORM_EVOLUTION.md)** — The manifesto. Why the platform is entering an expansion era, what the layer stack is, and what must never change.
*Read first because it defines the map every other document is a region of.*

**2. [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md)** — What an Asset is: one universal model spanning stocks, funds, gold, crypto, bonds, cash, and property, described by capabilities rather than branches.
*Read second because everything downstream — data, identity, portfolios, brokers — is expressed in terms of this Asset.*

**3. [MARKET_DATA_PLATFORM.md](MARKET_DATA_PLATFORM.md)** — How information from the outside world becomes trusted canonical data: discovery, resolution, routing, normalization, validation.
*Read third because it introduces the pipeline through which the universal Asset model is actually fed.*

**4. [PROVIDER_INTERFACE.md](PROVIDER_INTERFACE.md)** — The contract at the outer edge of that pipeline: providers as witnesses, adapters as translators, and the guarantee that no engine ever knows which vendor supplied its data.
*Read fourth because it is the detailed close-up of the Market Data Platform's outermost boundary.*

**5. [ASSET_REGISTRY.md](ASSET_REGISTRY.md)** — The authority at the center of the pipeline: how asset identity is minted, defended, and kept permanent, so that one real-world instrument always maps to exactly one internal Asset.
*Read fifth because identity is the keystone: the documents before it explain why identity is hard; the documents after it depend on identity being solved.*

**6. [PORTFOLIO_DOMAIN_MODEL.md](PORTFOLIO_DOMAIN_MODEL.md)** — What a Portfolio is: a strategy, a policy, and an accounting boundary — not a collection of assets. Includes the Investment Universe, policy surface, benchmarks, and the Wealth hierarchy.
*Read sixth because it defines the boundary inside which all accounting truth lives, which the final document must respect.*

**7. [BROKER_ACCOUNT_DOMAIN.md](BROKER_ACCOUNT_DOMAIN.md)** — How real brokerage accounts relate to that boundary: accounts as transaction sources and custody facts, imports as reconciliation, cash meaning owned by the portfolio.
*Read seventh because it stands where the two halves meet: the import machinery of documents 3–5 applied to the accounting boundary of document 6.*

**8. [TRANSACTION_DOMAIN_MODEL.md](TRANSACTION_DOMAIN_MODEL.md)** — What a Transaction is: the immutable business event, the canonical vocabulary, and the append-only stream from which all accounting, analytics, and evaluation are derived.
*Read eighth because it is the innermost document: every document before it explains how facts reach the ledger; this one defines the fact itself, and every accounting-related domain stands on it.*

**9. [CORPORATE_ACTION_DOMAIN.md](CORPORATE_ACTION_DOMAIN.md)** — How the world's restructurings (splits, mergers, spin-offs, redemptions) become facts: the adjudication bridge between Asset Identity and Canonical Transactions, owning neither.
*Read ninth because it is the first pure adjudication domain: it presumes both permanent authorities — the Registry and the ledger — and defines the disciplined path by which one real-world event lands consistently in both.*

**10. [EXECUTION_DOMAIN.md](EXECUTION_DOMAIN.md)** — How intent becomes history: the decision record binding AI recommendations, human judgment, and canonical transactions — the platform's second permanent memory.
*Read last because it is the second adjudication domain and the intelligence layer's only gate to the ledger: it presumes everything before it, and every evaluation the platform makes about itself stands on its record.*

A shorthand for the whole sequence: documents 1–2 define **what things are**, documents 3–5 define **how the world gets in**, documents 6–8 define **where truth is kept**, and documents 9–10 define **how changes — the world's and the user's — reach the truth**.

### Document Dependencies

The reading order is not arbitrary — it follows the dependency chain between the documents. Each document assumes the vocabulary of everything above it:

```
PLATFORM_EVOLUTION              the map: layers, philosophy, permanence
        │
        ▼
UNIVERSAL_ASSET_ARCHITECTURE    what an Asset is
        │
        ▼
MARKET_DATA_PLATFORM            how outside claims become canonical data
        │
        ▼
PROVIDER_INTERFACE              the contract at the pipeline's outer edge
        │
        ▼
ASSET_REGISTRY                  the identity authority
        │
        ▼
PORTFOLIO_DOMAIN_MODEL          the accounting boundary
        │
        ▼
BROKER_ACCOUNT_DOMAIN           custody, imports, transaction sources
        │
        ▼
TRANSACTION_DOMAIN_MODEL        the immutable event: the platform's permanent memory
        │
        ▼
CORPORATE_ACTION_DOMAIN         adjudicating the world's restructurings into both authorities
        │
        ▼
EXECUTION_DOMAIN                adjudicating the user's intent into the ledger; the decision record
```

An arrow means *"depends on the document above"*: PORTFOLIO_DOMAIN_MODEL depends on ASSET_REGISTRY (a portfolio's Investment Universe is expressed in canonical assets), which in turn depends on PROVIDER_INTERFACE and MARKET_DATA_PLATFORM (identity claims arrive through that pipeline), and so on up to the manifesto.

The practical rule this diagram gives an author: **when writing a new document, find where it attaches to this chain, and read everything above that point first.** A future Tax Engine document, for example, attaches below TRANSACTION_DOMAIN_MODEL and CORPORATE_ACTION_DOMAIN — so its author reads the entire chain before writing a word.

### Document Type Legend

The `docs/` tree contains more than this handbook, and the names can look similar. Three kinds of documents exist, at three levels of permanence:

```
ARCHITECTURE       what things ARE — boundaries, ownership, meaning
     │             → this handbook: the 7 domain documents in docs/architecture/
     │               (changes rarely; a boundary move is a major event)
     ▼
DOMAIN RULES       what the platform has DECIDED — rules and their reasons
     │             → ../engineering/DECISION_LOG.md, ../engineering/ENGINEERING_PRINCIPLES.md,
     │               ../investment/OPTIMIZER_PHILOSOPHY.md, ../investment/PORTFOLIO_CALCULATION_RULES.md
     │               (grows steadily; decisions are appended, rarely reversed)
     ▼
IMPLEMENTATION     how the system is BUILT today — and when it changes next
                   → ARCHITECTURE.md (as built), ROADMAP.md (what comes next)
                     (changes constantly; always trust it over memory)
```

Reading downward: architecture defines the boundaries, domain rules govern behavior inside them, and implementation is the current — always temporary — realization of both. When two documents seem to disagree, the one higher in this legend states the intent; the one lower states today's reality.

Shared vocabulary for all three levels is defined in [../GLOSSARY.md](../GLOSSARY.md).

---

## 3. Architecture Layers

The platform is organized as a flow: raw claims from the outside world are progressively refined into canonical facts, those facts are recorded inside an accounting boundary, and everything analytical is derived — never stored — from what was recorded.

```
┌───────────────────────────────────────────────────────────┐
│                      External World                       │
│     market data vendors · exchanges · brokers · users     │
└─────────────────────────────┬─────────────────────────────┘
                              │  raw claims, foreign symbols
                              ▼
┌───────────────────────────────────────────────────────────┐
│                         Providers                         │
│   adapters: witnesses of the world, translators at the    │
│   boundary — never authorities, never visible to engines  │
└─────────────────────────────┬─────────────────────────────┘
                              │  normalized observations
                              ▼
┌───────────────────────────────────────────────────────────┐
│                   Market Data Platform                    │
│   discovery · resolution · routing · validation · cache   │
│   turns outside claims into trusted canonical data        │
└─────────────────────────────┬─────────────────────────────┘
                              │  claims about identity
                              ▼
┌───────────────────────────────────────────────────────────┐
│                      Asset Registry                       │
│   the identity authority: one real-world instrument ↔     │
│   one permanent asset_id; symbols are evidence, not keys  │
└─────────────────────────────┬─────────────────────────────┘
                              │  canonical assets
                              ▼
┌───────────────────────────────────────────────────────────┐
│                     Portfolio Domain                      │
│   strategy + policy + accounting boundary; the Investment │
│   Universe decides what may enter each portfolio          │
└─────────────────────────────┬─────────────────────────────┘
                              │  attributed transactions
                              ▼
┌───────────────────────────────────────────────────────────┐
│                      Broker Accounts                      │
│   transaction sources and custody facts; imports become   │
│   canonical ledger events, provenance preserved           │
└─────────────────────────────┬─────────────────────────────┘
                              │  the transaction ledger
                              ▼
┌───────────────────────────────────────────────────────────┐
│                     Portfolio Engine                      │
│   holdings, cash, and positions maintained per portfolio  │
└─────────────────────────────┬─────────────────────────────┘
                              │  recorded events, in order
                              ▼
┌───────────────────────────────────────────────────────────┐
│                       Replay Engine                       │
│   the accounting authority: deterministic reconstruction  │
│   of all state from the ledger alone                      │
└─────────────────────────────┬─────────────────────────────┘
                              │  replayed truth
                              ▼
┌───────────────────────────────────────────────────────────┐
│                         Analytics                         │
│   performance, attribution, risk — derived, never stored  │
│   as independent truth                                    │
└─────────────────────────────┬─────────────────────────────┘
                              │  measured outcomes
                              ▼
┌───────────────────────────────────────────────────────────┐
│                       AI Evaluation                       │
│   judgment about decisions: grading, calibration, trust — │
│   consuming truth, never producing it                     │
└───────────────────────────────────────────────────────────┘
```

Two properties of this picture matter more than any single box:

- **Truth flows downward through refinement, never upward by decree.** A provider cannot tell the Registry what an asset is; a broker cannot tell the Replay Engine what a balance is. Each layer may only *claim* to the layer below it, and each layer validates what it receives.
- **The middle is stable; the edges churn.** Providers, brokers, and user interfaces are expected to be replaced repeatedly over the platform's life. The Registry, the Portfolio boundary, and the Replay Engine are expected to survive all of those replacements unchanged.

---

## 4. Core Design Principles

Seven documents, written months apart, keep arriving at the same small set of convictions. They are the platform's actual architecture; the documents are elaborations of them.

**Identity is permanent, and only the platform can grant permanence.** Assets, portfolios, and broker accounts each carry an internal identifier that is minted once and never reassigned. Everything the outside world calls a thing — tickers, ISINs, account numbers, vendor symbols — is treated as *evidence* about identity, never as identity itself. Names change; the ledger is forever; therefore the ledger is never keyed by a name.

**External parties are witnesses, never authorities.** Providers witness the world's prices; brokers witness the user's own history. Both may inform the platform; neither may overwrite it. When a witness disagrees with recorded truth, the disagreement is surfaced as a finding — it is never silently resolved in the witness's favor.

**The Portfolio is the accounting boundary.** Every transaction belongs to exactly one portfolio; every flow is classified by whether it crosses that boundary, not by where money physically moved. Custody, provenance, and presentation all live outside the boundary and can therefore change without touching accounting truth.

**Business logic consumes canonical models only.** No engine knows which vendor supplied a price or which broker supplied a trade. The moment data crosses into the platform it is expressed in platform vocabulary, and the engines' code paths are identical regardless of origin. This is what makes the edges replaceable.

**Replay is deterministic.** All portfolio state is reconstructible from the transaction ledger alone, in a fixed order, with one implementation per business rule. Nothing downstream of the ledger is a source of truth; everything downstream is a derivation that can be thrown away and rebuilt.

**Capabilities over implementations.** Assets declare what they can do; providers declare what they can supply; broker adapters declare what they can import. Routing and validation are generic matching against those declarations. Adding a new asset class, vendor, or institution adds vocabulary — it never adds branches inside an engine.

**Degrade loudly, repair explicitly.** Missing data, ambiguous identity, and failed imports are first-class recorded outcomes, never guesses or silent fills. Anything load-bearing is repaired through explicit, auditable actions — never auto-corrected in place. Recorded history is append-only: corrections are new events, and closed is never deleted.

**Judgment and description are kept apart.** Deterministic layers compute; humans and clearly-bounded evaluation layers judge. Portfolio analytics judge performance against intent; account and wealth views merely describe. When a layer cannot decide something deterministically, it asks — it never guesses.

---

## 5. Current Coverage

The handbook currently defines ten architecture domains:

- **Platform** — the layer stack, expansion philosophy, and permanence guarantees (PLATFORM_EVOLUTION.md).
- **Asset** — the universal asset model and its capability vocabulary (UNIVERSAL_ASSET_ARCHITECTURE.md).
- **Market Data** — the pipeline from outside claim to canonical fact (MARKET_DATA_PLATFORM.md).
- **Provider** — the contract at the outermost boundary of that pipeline (PROVIDER_INTERFACE.md).
- **Asset Identity** — the registry that mints and defends permanent identity (ASSET_REGISTRY.md).
- **Portfolio** — the strategy, policy, and accounting boundary at the platform's core (PORTFOLIO_DOMAIN_MODEL.md).
- **Broker** — custody, transaction sources, and the import boundary (BROKER_ACCOUNT_DOMAIN.md).
- **Transaction** — the immutable business event, canonical vocabulary, and append-only ledger semantics (TRANSACTION_DOMAIN_MODEL.md).
- **Corporate Actions** — announcements, adjudication, and the consistent landing of structural events in both the Registry and the ledger (CORPORATE_ACTION_DOMAIN.md).
- **Execution** — the decision record: intent, approval, lifecycle, and the one gate through which recommendations become transactions (EXECUTION_DOMAIN.md).

Together they cover the full path from the outside world to the ledger. What they deliberately do not yet cover is listed in the next section.

---

## 6. Planned Architecture

The following domains are expected to receive documents of their own as the platform grows. They are listed here for orientation only — nothing below is designed yet, and nothing in the existing documents should be read as pre-deciding them.

- **Multi Currency** — the platform-wide treatment of FX beyond the boundaries already sketched in the broker and portfolio documents.
- **Goal Planning** — goals as durable objects connecting portfolios to intent over time.
- **Tax Engine** — jurisdiction-aware treatment of realized gains, dividends, and tax-advantaged wrappers.
- **Wealth Domain** — the descriptive layer above portfolios: net worth, allocation across boundaries, household views.
- **Risk Engine** — risk as a domain concept spanning exposure, concentration, and scenario reasoning.
- **Execution Analytics** — the study of intent-versus-outcome divergence the Execution Domain preserves: slippage, delay cost, fill quality.

When one of these is written, it joins the reading order at the point where its dependencies are satisfied, and this README is updated.

---

## 7. Contribution Guidelines

Future architecture documents should feel like chapters of the same book. Concretely:

- **Maintain consistency.** Reuse the established structure: an italic preamble stating scope and what the document is *not*, numbered sections, a closing set of design principles, and a Related Documents section. Match the register of the existing documents — declarative, grounded, written for a reader years away.
- **Reference existing documents; do not restate them.** If a concept is owned by another document, link to it and use its vocabulary. Each concept has exactly one home; every other mention is a pointer.
- **Avoid duplication by assigning ownership.** When two documents share a boundary (as Market Data and Provider Interface do), say explicitly in each preamble which side of the boundary each document owns.
- **Keep implementation out.** No database schemas, no SQL, no API specifications, no code, no file formats, no vendor recommendations. If a sentence could only be verified by reading the codebase, it belongs in `ARCHITECTURE.md`, not here.
- **Follow domain-driven terminology.** Use the platform's own nouns — Asset, Registry, Portfolio, Ledger, Replay, Provider, Broker Account — as defined in [../GLOSSARY.md](../GLOSSARY.md) and in these documents. If a new document needs a new noun, define it once, precisely, and add it to the glossary.
- **Ground abstractions in real history.** The strongest passages in this handbook earn their rules from incidents the platform actually lived through. Cite the lesson, anonymize the vendor.
- **Write for the boundary, not the feature.** An architecture document's job is to say what a thing *is*, who owns it, and what may never cross its edge. Features come and go inside boundaries; the documents describe the boundaries.
- **Keep this README current.** When a document is added: increment the document count, bump the major version, refresh *Last Updated*, insert the document into the reading order and dependency chain, and move its domain from Planned Architecture to Current Coverage. When an existing document is materially revised, bump the minor version. The version block exists so that references like "as of Handbook v1.0" stay meaningful years later.

---

## Related Documents

- [ARCHITECTURE.md](ARCHITECTURE.md) — implementation reference for the system as built
- [ROADMAP.md](ROADMAP.md) — phased delivery plan
- [../GLOSSARY.md](../GLOSSARY.md) — shared vocabulary
- [../engineering/ENGINEERING_PRINCIPLES.md](../engineering/ENGINEERING_PRINCIPLES.md) — how the platform is built
- [../engineering/DECISION_LOG.md](../engineering/DECISION_LOG.md) — the architectural decisions behind these boundaries
- [../investment/OPTIMIZER_PHILOSOPHY.md](../investment/OPTIMIZER_PHILOSOPHY.md) — the investment philosophy the platform serves
