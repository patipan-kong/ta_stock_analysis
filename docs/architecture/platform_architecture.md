# Portfolio Intelligence Platform Architecture

_The architectural constitution of the platform._

_**Constitution v1.1.** v1 (ratified 2026-07-10) comprises Sections 1–10 and is preserved unmodified. v1.1 (2026-07-10) added Sections 11–12 — Architecture Governance and Canonical Vocabulary — as purely additive amendments, recorded in [DECISION_LOG.md](../engineering/DECISION_LOG.md)._

_This document is not an implementation guide, not a technical design document, and not an ADR. It defines the permanent architectural philosophy, the domain boundaries, and the laws that bind every future capability — and it is written to remain valid as every implementation beneath it is replaced. Where this document and the rest of the Architecture Handbook cover the same ground, they are deliberately consistent; a divergence between them is a defect to be reconciled through [DECISION_LOG.md](../engineering/DECISION_LOG.md), never tolerated as drift. For the system as actually built today, read [ARCHITECTURE.md](ARCHITECTURE.md); for when the gaps close, read [ROADMAP.md](ROADMAP.md)._

---

## 1. Purpose

Portfolio Intelligence exists so that a person can entrust their financial life to a system and **verify** — not hope — that the trust is deserved.

That sentence contains the whole architecture. Most financial software asks to be believed: it shows a balance, a return, a recommendation, and the user's only option is confidence or doubt. This platform is built on the opposite premise. Every number is a derivation of recorded events and can be replayed. Every recommendation states its evidence and its reasoning. Every judgment the system has ever made is recorded immutably and graded against what actually happened, so that the system's competence is a measured fact, not a marketing claim.

The platform began as a stock analysis tool. It has become an investment intelligence platform — deterministic accounting, a replayable ledger, portfolio analytics, an AI decision engine, execution intelligence, recommendation evaluation, and a permanent asset identity registry. It is now becoming a multi-asset investment platform, and it is headed toward being a personal wealth platform: a system that can hold everything a person owns, everything they owe, everything they intend, and advise them with an auditable track record.

At every stage, the product is the same thing: **provable financial truth, and accountable judgment on top of it.** Features change; that does not.

---

## 2. Design Philosophy

Five ideas govern everything below. They are stated as philosophy rather than rules because rules can be satisfied by the letter; philosophy explains what the rules are *for*.

### 2.1 Truth and judgment are different substances

A portfolio's balance and an opinion about what to buy are not two points on a spectrum — they are different kinds of thing, produced by different machinery, governed by different laws. Truth is computed deterministically from recorded events, and two runs must agree forever. Judgment is formed from evidence, is allowed to be wrong, and is graded afterward. The platform's deepest structural commitment is that these two substances never blend: no judgment machinery ever produces truth, and truth machinery never quietly embeds opinion. Nearly every law in Section 4 is a corollary of this one separation.

### 2.2 Trust is accumulated, never asserted

A system that advises on someone's wealth earns trust only one way: by making claims, recording them where they cannot be edited, and letting reality grade them. This is why recorded history is immutable, why evaluation is an independent power rather than a feature of the decision engine, and why the platform maintains a permanent memory of its own recommendations alongside the user's transactions. The platform's defining asset is a trustworthy past — its own as much as the user's.

### 2.3 The engines are the treasure; the edges are the frontier

The deterministic core — ledger, replay, metrics — carries years of accumulated correctness: hardened invariants, regression-encoded accounting rules, repaired incidents. That accumulation is the platform's capital, and it is spent, never earned back, by rewriting. Value now grows by *multiplication*: every new asset class, data source, and institution that the existing engines can serve multiplies every capability already built. Therefore the core changes rarely and constitutionally, the edges change constantly and cheaply, and the architecture is precisely the gradient between them.

### 2.4 Boundaries do the work

The platform's worst historical defects were all boundary failures — a provider's symbology leaking into business logic, an import contaminating returns, an external format carrying meaning into an engine. So the architecture invests where the failures were: everything entering the platform is normalized into canonical vocabulary, tagged with provenance and confidence, and resolved to permanent identity *at the boundary*. Inside, engines speak only platform language. A capability is judged not by what it does when it works but by whether its failure is contained at its edge.

### 2.5 The human is sovereign

The platform records a person's financial life and advises on it. It does not own either. Automated inputs propose; the human confirms. Recommendations argue; the human decides. Autonomy can be delegated — explicitly, narrowly, revocably — but it is never assumed and never eroded by increments of convenience. A wealth platform that quietly acts on its own beliefs has confused itself with the person it serves.

---

## 3. Architecture Goals

The qualities the platform must preserve at any size, in any era. Each is stated with its falsifiable test, because a goal that cannot be failed is a slogan.

- **Deterministic.** Same ledger, same price history, same rules → same state, on any machine, at any future date. *Test: replay of any historical period reproduces it exactly.*
- **Reproducible & auditable.** Every number traces to the recorded events and inputs that produced it; every record carries provenance. *Test: any figure shown to the user can be decomposed to ledger events on demand.*
- **Explainable.** Every recommendation states its evidence, its reasoning, and its confidence; every evaluation shows its scoring basis. *Test: "why?" always has an answer that does not require reading source code.*
- **Multi-asset by design.** The engines know what an *asset* is — ownable, valuable, transactable, flow-generating — never what a *stock* is. *Test: a new asset class is added by describing it, not by editing an engine.*
- **Provider-independent.** No engine knows where a price, a trade, or a document came from. *Test: losing any single external vendor is an operational event, never an architectural one.*
- **Extensible by addition.** New capability arrives as a new adapter, asset definition, or consumer of recorded objects — the existing engines untouched. *Test: the diff for a new integration contains no engine changes.*
- **AI-assisted, evidence-driven.** AI forms beliefs from deterministic evidence and explains them; it never replaces the evidence and never performs the arithmetic. *Test: disabling every AI layer leaves accounting, holdings, and history fully intact.*
- **Loudly degraded.** Every adapter, provider, and engine can fail; none may fail silently. *Test: every fallback path is observable in operation.*
- **Humane.** The platform presents calm to those who want calm and depth to those who want depth, without maintaining two truths. *Test: both presentation modes derive from the same numbers.*

---

## 4. Architecture Principles

The constitutional laws. Everything else in this document is direction; this section is binding. A change that violates one of these is wrong by definition, whatever its benchmark or deadline says. Deliberately breaking one requires amending this document first, with reasoning recorded in [DECISION_LOG.md](../engineering/DECISION_LOG.md) — never by drift, never by "temporary" exception.

**Law 1 — The ledger is the single source of truth.**
Every asset the platform will ever hold exists in the system because a ledger event says so. Every balance, holding, snapshot, and metric — for every asset class, forever — is a derivation of ledger events. No feature may create portfolio truth that does not live in the ledger.

**Law 2 — Recorded history is immutable.**
Transactions, snapshots-as-computed, recommendations, decisions, evaluations, grades: once written, never edited. Corrections are new records with their own provenance. Closed is never deleted.

**Law 3 — Holdings are derived.**
Positions, cash balances, cost bases, and every analytic on top of them are disposable derivations, rebuildable from the ledger at any time. Nothing derived is ever treated as an independent source of truth, and no derivation is ever "patched" in place of correcting its inputs.

**Law 4 — Replay is deterministic and reproducible.**
No wall-clock dependence, no provider dependence, no randomness anywhere in the accounting path. Determinism is not an implementation preference; it is what makes validation, repair, audit, and trust possible at all.

**Law 5 — Asset identity is permanent.**
An identity, once minted, is never reassigned and never reused. Everything the outside world calls an instrument — tickers, ISINs, vendor symbols, account labels — is *evidence about* identity, never identity itself. Names change; the ledger is forever; therefore truth is never keyed by a name.

**Law 6 — Identity is resolved decisively or not at all.**
Resolution happens at the boundary, when a fact enters. Ambiguity is surfaced for adjudication, never guessed away; a conflict between evidence sources is a recorded finding, never a silent override. Once a fact is recorded, its identity resolution travels with it — replay never re-asks the question.

**Law 7 — AI never performs accounting.**
No model output, however capable the model, ever writes a ledger event, adjusts a balance, computes a cost basis, or "corrects" a number. AI reads derived state and produces beliefs, recommendations, and explanations. The boundary between judgment and arithmetic moves only by constitutional amendment.

**Law 8 — Evaluation observes; it never touches.**
Anything that grades, attributes, or calibrates consumes recorded objects and produces new ones. It never edits what it judges, never reaches upstream, never rewrites the past to flatter the present — and it never influences a decision already recorded. Evaluation may shape the *future* only through the governed configuration path, in the open.

**Law 9 — Every business rule has exactly one implementation.**
Platform growth multiplies consumers; it must never multiply implementations. No engine, adapter, asset class, or convenience gets its own copy of a calculation that already has an owner. When the owner cannot serve a new case, the owner is extended — deliberately, minimally, with its existing test corpus intact.

**Law 10 — The core never knows the edge.**
No engine contains provider names, broker names, input-format logic, or asset-class special cases. If the core needs to know where something came from, the boundary has failed, and the boundary — not the core — is what gets fixed.

**Law 11 — Everything enters through the hallway.**
Every fact, from every source, becomes a canonical, provenance-tagged, confidence-labeled event *before* it reaches the accounting core. Automated inputs land as proposals subject to review; nothing bypasses normalization, however trusted the source. Deduplication and conflict resolution are boundary work, never compensating heuristics inside engines.

**Law 12 — The human owns the ledger and the decision point.**
The recorded financial truth of a person's life is never silently written by a machine, and no recommendation executes itself. Autonomy exists only as explicit, specific, revocable delegation.

**Law 13 — Failure is loud.**
Every adapter, provider, engine, and AI layer that degrades does so observably. Fallbacks are acceptable; silent failures are not. A platform of many edges is a platform of many failure modes, and observability of degraded modes is the price of having edges.

**Law 14 — Explainability is a fiduciary duty.**
Every number is traceable, every recommendation reasoned, every evaluation evidenced. As the platform grows toward a person's whole financial life, the duty grows with it — a system advising on someone's retirement owes *more* explanation, not less.

**Law 15 — Correctness outranks everything.**
Every conflict between a capability and a correct number resolves in favor of the number. This was true at the first commit and must be true at v10. A wrong number explained beautifully is worse than a right number explained plainly.

---

## 5. Platform Layers

The platform is a refinement of meaning, from *what exists* to *what a person experiences*. Each layer answers one question, derives only from the layers beneath it, and is consumed only by the layers above it.

```
        IDENTITY        what things are
            ↓
        OBSERVATION     what the world reports about them
            ↓
   ┌──→ TRUTH           what actually happened            ┐
   │        ↓                                             │
 (gate)  KNOWLEDGE      what it means                     │  observed by
   │        ↓                                             ├──  TRUST
outside  JUDGMENT       what to do about it               │  (reads records,
 world      ↓                                             │   writes only
        EXPERIENCE      how a person meets all of it      ┘   its own)
```

**Identity** — Before anything can be owned, valued, or transacted, the platform must know what it *is*, permanently and unambiguously. Identity is the root layer because every other layer's statements are statements *about* identified things. It depends on nothing inside the platform.

**Observation** — The world continuously reports on identified things: prices, calendars, exchange rates, regimes, news, macro conditions. Observations are evidence, not truth — they inform valuation and judgment, but they never become ledger events and no observation source is ever an authority.

**Truth** — What actually happened: the append-only record of financial events, and the deterministic machinery that derives state from it. Truth is guarded by a gate: facts from the outside world (and intents from the user) enter only through the normalization-and-review boundary. This is the layer the whole platform exists to protect.

**Knowledge** — Meaning derived from truth and observation: performance, risk, attribution, exposure, net worth, progress toward goals. Knowledge is always recomputable, never independently stored as truth, and always traceable back down the stack.

**Judgment** — Beliefs and plans formed on top of knowledge: what to buy, what to trim, what to leave alone, and why. Judgment is the only layer where being wrong is legitimate — which is exactly why its outputs are recorded immutably and graded.

**Experience** — Where a human meets the platform: dashboards, briefs, conversation, notification, control. Experience renders and explains; it never computes, and it can never make a number say something the layers below did not.

**Trust** — deliberately drawn *beside* the stack, not in it. A common architectural mistake — present in early drafts of this very document — is to place Evaluation as a stage between Judgment and Experience, as if grading were a step in the pipeline. It is not. Trust is an **observer plane**: it reads the immutable records of Judgment and Truth, measures them against each other, and writes only its own records. Nothing operational depends on it; it depends on everything being recorded. Placing it in the flow would tempt exactly the coupling Law 8 forbids — a judge sharing an office with the defendant.

Two rules give the stack its meaning, and they are laws, not descriptions:

- **Truth flows up; nothing flows down.** A higher layer needing something changed below goes through the boundary that owns it — a proposed event, a review queue, a human decision. The Experience layer cannot write a transaction; Judgment cannot adjust a price; nothing edits Truth in place.
- **The middle is stable; the edges churn.** Identity and Truth change rarely and constitutionally. Observation sources, ingestion adapters, and Experience change constantly and cheaply. A design that requires a core change to accommodate an edge event is, by that fact alone, wrong.

---

## 6. Platform Domains

Nine domains partition the platform. A domain is a boundary of ownership and meaning, not a module, a team, or a deployment unit. Each domain owns some portion of the platform's vocabulary exclusively: every concept has exactly one home, and every other mention is a reference.

The domains map onto the layers as follows:

| Layer | Domain(s) |
|---|---|
| Identity | Asset Foundation |
| Observation | Market Intelligence |
| Truth (and its gate) | Ledger & Accounting · Connectivity & Ingestion |
| Knowledge | Portfolio Intelligence · Wealth Intelligence |
| Judgment | Decision Intelligence |
| Trust (observer) | Trust & Evaluation |
| Experience | Experience Platform |

Wealth Intelligence deserves one clarification: it is not a new layer above Portfolio Intelligence but a **widening of scope** across the Knowledge and Judgment layers — from "this portfolio" to "this life." It is a domain because it owns vocabulary (goals, net worth, plans) that no other domain owns; it is not a layer because it obeys the same physics as its neighbors.

---

### 6.1 Asset Foundation

**Purpose.** To answer, permanently and unambiguously, the question every other domain presumes: *what is this thing?*

**Responsibilities.** Minting and defending permanent asset identity. Adjudicating identity evidence — symbols, listings, renames, corporate restructurings — into identity facts. Classification along the platform's dimensions (type, sector, region, and dimensions not yet needed). Defining asset *behavior*: what an asset class can do — its unit semantics, valuation cadence, flow types, lifecycle vocabulary — so that engines consume capability descriptions rather than type branches. Making the catalog of everything ownable searchable and discoverable.

**Owns.** The asset identity space. The classification taxonomy. The asset-definition vocabulary ("assets are plugins" — this domain is the plugin library). The linkage between related identities (an instrument and its depositary receipt; a fund and its share classes).

**Depends on.** Nothing inside the platform. It is the root domain. It *receives evidence* from Market Intelligence and Connectivity & Ingestion, but evidence is testimony, not dependency: witnesses inform the Registry; they never instruct it.

**Provides.** Canonical asset references — the nouns of every other domain's sentences. Classification facts for exposure and constraint reasoning. Behavior descriptions the engines use to serve any asset class without knowing its name.

---

### 6.2 Market Intelligence

**Purpose.** To know what identified things are *worth*, and what the world around them is doing — as evidence, never as truth.

**Responsibilities.** Valuation of any identified asset over time, at whatever cadence the asset's nature allows — ticks for equities, daily marks for funds, appraisals for property. Market calendars and currency conversion context. Market-state understanding: regime, volatility, breadth. News and event understanding as inputs to belief. Macro context. Absorbing every external data source behind adapters so that no consumer ever knows a vendor's name, and labeling every observation with its source's confidence.

**Owns.** Canonical observations: prices, histories, calendars, rates, regimes, event interpretations. The provider-independence boundary for market data.

**Depends on.** Asset Foundation (observations are statements about identified things).

**Provides.** Worth and context to Portfolio Intelligence (valuation), Decision Intelligence (evidence for beliefs), Wealth Intelligence (planning assumptions), and Trust & Evaluation (the reality against which judgments are graded). It never writes to the ledger: a price is not an event in a person's financial life.

---

### 6.3 Ledger & Accounting

**Purpose.** To be the platform's memory: the immutable record of what happened, and the deterministic machinery that derives provable state from it.

**Responsibilities.** The append-only event record and its canonical vocabulary, extended over time to every flow a financial life contains. The accounting boundary — every event belongs to exactly one portfolio, and every flow is classified by whether it crosses that boundary. Deterministic derivation of holdings, cash, cost basis, and valuation-in-time. Conservation guarantees: nothing appears or disappears without an event saying why. Validation of the record's integrity, and explicit, auditable repair when integrity fails — detection always read-only, correction always a new recorded event.

**Owns.** Financial truth. The transaction vocabulary. The accounting semantics of every asset class (which are described by Asset Foundation but *enforced* here). The canonical return and metric formulas' inputs.

**Depends on.** Asset Foundation, in a deliberately frozen way: events reference permanent identities, but identity resolution happens at the boundary *before* recording, and replay never re-resolves. The accounting path consults no live authority — that is what keeps it deterministic.

**Provides.** Replayable truth: the ground every upper domain stands on and the audit trail behind every number the platform will ever show.

---

### 6.4 Connectivity & Ingestion

**Purpose.** To be the only way facts enter the platform: many doors, one hallway.

**Responsibilities.** An adapter per source — manual entry, file exports, institutional statements, broker and bank connections, corporate-action and income feeds, parsed documents — each fluent in its source's dialect, each containing that source's chaos at the boundary. Translation of everything into canonical, provenance-tagged, confidence-labeled event proposals. Deduplication and conflict detection across sources, with provenance as the instrument. The review-and-reconciliation discipline through which proposals become recorded truth — human-confirmed by default, auto-accepted only under explicit, revocable, per-source delegation.

**Owns.** The boundary with the outside world's *facts* (as Market Intelligence owns the boundary with its *observations* — the two share the witness-never-authority contract). Provenance at the moment of capture. The proposal/review/reconciliation vocabulary.

**Depends on.** Asset Foundation (every incoming fact is resolved to identity, decisively or not at all). Ledger & Accounting's vocabulary (adapters produce canonical events; they never invent dialects of truth).

**Provides.** Proposed ledger events with lineage. Reconciliation findings when sources disagree with each other or with recorded truth. The multiplication effect: every new door serves every existing engine.

---

### 6.5 Portfolio Intelligence

**Purpose.** To turn truth and worth into meaning: what the portfolio did, what it holds, what it risks, and why.

**Responsibilities.** Valuation of holdings as derived views. Performance measurement under the canonical formulas — cash-flow aware, contamination-free, one implementation per rule. Attribution: decomposing outcomes by allocation, selection, timing, regime, and factor. Risk and exposure: concentration, drawdown, volatility, factor tilts, and their evolution. Benchmarking against declared alternatives. Aggregation across portfolios toward household-level views.

**Owns.** The canonical derived measures and their semantics. The attribution vocabulary. The meaning of "performance" on this platform.

**Depends on.** Ledger & Accounting (truth), Market Intelligence (worth), Asset Foundation (identity and classification, so that exposure means the same thing across asset classes).

**Provides.** Knowledge — to Decision Intelligence as the factual basis for beliefs, to Wealth Intelligence as the building blocks of net worth and progress, to Trust & Evaluation as the measured outcomes judgments are graded against, and to Experience Platform as everything worth showing.

---

### 6.6 Decision Intelligence

**Purpose.** To form judgment: beliefs about assets, recommendations about portfolios, and plans for acting — always evidenced, always explained, never self-executing.

**Responsibilities.** Belief formation from deterministic evidence, including adversarial review among independent perspectives — belief must survive challenge before it becomes recommendation. Policy and constraint governance: the deterministic envelope of persona, regime, and safety limits inside which every recommendation must fit, enforced by arithmetic, not by asking the AI nicely. The separation of belief from execution: *what should be true* is one object; *what to do about it* is another, justified independently, because every trade has cost and is guilty until proven necessary. Execution planning: funding, sizing, sequencing, timing. Intake of human ideas into the same disciplined review as machine-originated ones. The immutable decision record: what was recommended, on what evidence, and what the human decided.

This domain has its own constitution — [OPTIMIZER_PHILOSOPHY.md](../investment/OPTIMIZER_PHILOSOPHY.md) — which governs its internal structure. This document defers to it entirely within the domain's boundary and binds it at that boundary.

**Owns.** Beliefs, recommendations, plans, and decision records. The policy envelope. The judgment/arithmetic boundary's judgment side.

**Depends on.** Portfolio Intelligence (knowledge), Market Intelligence (evidence and context), Asset Foundation (identity and classification), Ledger & Accounting (read-only truth). In later eras: Wealth Intelligence (goals and tax posture as first-class decision context).

**Provides.** Recommendations and plans to the Experience Platform for human decision. Immutable decision records to Trust & Evaluation. Approved intent that becomes ledger events only through the same gated, human-owned path as every other fact — a recommendation is never a transaction.

---

### 6.7 Trust & Evaluation

**Purpose.** To answer, with evidence, the only question that ultimately matters about an advising system: *was it right?*

**Responsibilities.** Grading every recommendation against what subsequently happened. Maintaining the counterfactuals — the paths not taken, both the pure-model path and the human-decision path — so that human and machine judgment can be compared honestly. Calibration: whether the system's stated confidence matches its realized accuracy. Composing the evidence into a trust account the user can audit. And, in a later era, learning: turning the accumulated record into improved future parameters — through the governed configuration path, in the open, never by reaching into a live decision or a recorded past.

**Owns.** Grades, calibration records, counterfactual tracks, and the trust vocabulary. Its records are as immutable as the ledger's — an evaluation, once recorded, is history too.

**Depends on.** The records of Decision Intelligence, the truth of Ledger & Accounting, the measures of Portfolio Intelligence, and the reality provided by Market Intelligence — all read-only, by law.

**Provides.** Measured trustworthiness to the Experience Platform. Nothing else, to anyone, operationally: no domain's runtime behavior may depend on this domain being present. That independence is not a limitation; it is the entire source of its credibility.

---

### 6.8 Wealth Intelligence

**Purpose.** To widen the platform's frame from a portfolio to a life: everything owned, everything owed, everything intended.

**Responsibilities.** Net worth as a first-class derived view over every identified, ledgered thing a person has. Goals as durable objects — retirement, education, property, independence — connecting portfolios to intent over time, with progress measured rather than guessed. Cash-flow understanding: income, expenses, saving capacity, resilience. Planning semantics: the assumptions, horizons, and trade-offs that turn a goal into a plan. Tax and protection posture as context the Judgment layer must respect.

**Owns.** The life-level vocabulary: goals, plans, net worth, obligations, protection. No new physics — every wealth-level fact is still a ledger derivation; every wealth-level recommendation still flows through Decision Intelligence's discipline.

**Depends on.** Portfolio Intelligence, Ledger & Accounting, Asset Foundation, Market Intelligence. It is a consumer of the whole stack below it, which is exactly why it can exist without redesigning any of it.

**Provides.** Life context to Decision Intelligence — the difference between "a good trade" and "a good trade *for this person's retirement*." Meaning to the Experience Platform at the level users actually live at.

---

### 6.9 Experience Platform

**Purpose.** To be the membrane between the platform and the person: comprehension inward, intent outward — computing nothing, hiding nothing.

**Responsibilities.** Presentation in the platform's dual register — calm for those who want reassurance, depth for those who want evidence — over one set of numbers. The unified timeline: a person's financial life, the system's judgments, and the grades, as one stream. Notification: knowing what deserves attention and what deserves silence. The conversational surface — briefs, reviews, dialogue — that translates platform truth into human language without ever inventing content the lower layers cannot back. Capture of intent: decisions, confirmations, settings, delegations. And platform operations as the product grows shared: identity and access, workspaces, audit of who did what.

**Owns.** The rendering of everything and the truth of nothing. The interaction vocabulary. The operational shell.

**Depends on.** Every domain, read-only. Its writes are exclusively expressions of human intent, routed to the domain that owns the intended change.

**Provides.** The product, as the user knows it. Every other domain exists so this one has something worth showing.

---

## 7. Domain Relationships

### 7.1 The dependency law

```
                    Experience Platform
                            │ reads everything; writes only human intent
        ┌───────────┬───────┴────────┬──────────────┐
        ▼           ▼                ▼              ▼
   Wealth      Decision         Portfolio      Trust & Evaluation
Intelligence  Intelligence     Intelligence     (observer: reads
        │           │                │           records, writes only
        └─────┬─────┴───────┬────────┘           its own)
              ▼             ▼
       Ledger & Accounting  Market Intelligence
              ▲             │
              │ proposals   │
       Connectivity &       │
         Ingestion          │
              │             │
              └──────┬──────┘
                     ▼
              Asset Foundation
                     ▲
              (evidence flows in from the edges;
               instruction never does)
```

Dependencies point downward only. A domain may know of, call on, and build upon any domain beneath it; it may never depend on one above it. Asset Foundation depends on nothing. Experience Platform depends on everything. No cycles, no exceptions, no "just this once."

### 7.2 The three gates

Exactly three doorways exist through which anything changes recorded state, and all three are owned:

1. **The ingestion gate.** Facts from the outside world become truth only through Connectivity & Ingestion: normalized, provenance-tagged, resolved to identity, reviewed. (Laws 6, 11, 12.)
2. **The decision gate.** Intent becomes action only through a recorded decision — recommendation, human judgment, and outcome bound together immutably. A recommendation is never a transaction; the human (or their explicit, revocable delegation) is always between them. (Laws 7, 12.)
3. **The configuration gate.** Learning and tuning change future behavior only through governed, visible configuration — never by a model quietly adjusting itself, never by evaluation reaching into the machinery it grades. (Law 8.)

Everything else in the platform is derivation and display.

### 7.3 Boundaries that must never be crossed

| Forbidden crossing | Law | Why it is fatal |
|---|---|---|
| Any domain writing ledger events except through the ingestion or decision gates | 1, 11 | Truth created outside the ledger is truth that cannot be replayed, audited, or trusted |
| Trust & Evaluation writing to, or being operationally depended on by, any domain it observes | 8 | A judge the defendant funds is not a judge; an evaluation layer with write access is not an evaluation layer |
| Decision Intelligence (or any AI) touching accounting | 7 | The judgment/arithmetic boundary is the platform's load-bearing wall |
| Any engine containing provider, broker, format, or asset-class knowledge | 10 | Every such leak converts a replaceable edge into a permanent liability |
| Experience Platform computing a number | — | Two sources of a number is two numbers; presentation must be incapable of disagreeing with truth |
| A second implementation of an owned business rule | 9 | The platform's history includes exactly this failure; the scar is constitutional |
| Replay consulting a live authority (registry, provider, model) at replay time | 4, 6 | Determinism dies the moment reconstruction depends on the present |

### 7.4 Witnesses and authorities

A single pattern recurs at every edge, and naming it once prevents relitigating it: external parties are **witnesses, never authorities**. A market data vendor witnesses prices; a broker witnesses trades; a parsed statement witnesses history; a model witnesses patterns. Witnesses inform the domain that owns the question — identity evidence flows to Asset Foundation, price evidence to Market Intelligence, fact evidence to Connectivity & Ingestion — and the owning domain adjudicates. When witnesses disagree, the disagreement is a recorded finding. No witness ever overwrites recorded truth in its own favor.

---

## 8. Cross-cutting Principles

Some obligations belong to no domain because they belong to all of them. They are requirements on every capability, in every domain, in every era — and their corollary is structural: **none of them may ever appear as a feature, a module, or a box on a diagram.** A platform that builds an "explainability service" has already decided the rest of the platform doesn't have to explain itself.

- **Correctness.** Every domain resolves every conflict between capability and correct numbers in the numbers' favor. Correctness debt is paid before capability is built on top of it.
- **Determinism where truth is made.** Any path that produces or reproduces recorded state is deterministic. Judgment may be probabilistic; arithmetic never.
- **Explainability.** Every domain can answer "why?" about everything it produces, at the level of the person asking — the calm answer and the deep answer, both true.
- **Provenance & auditability.** Everything that enters carries its origin; everything recorded is attributable; everything derived is traceable. The question "where did this come from?" is answerable forever, about anything.
- **Observability & loud failure.** Every domain's degraded modes are designed, named, and visible. A capability is not done when it works; it is done when its failure is contained and observable.
- **Human sovereignty.** Every domain that touches truth or action preserves the human's ownership of both. Convenience never erodes the decision point.
- **One implementation per rule.** Every domain reuses the owner of a calculation or extends it — it never forks it.

---

## 9. Long-term Evolution

The platform's trajectory is known in outline:

```
Portfolio Platform → Investment Intelligence → Multi-Asset Platform → Wealth Platform → AI Wealth Advisor
```

The architectural claim of this document is that **every one of these transitions is absorbed by the nine domains without redesign** — each era adds vocabulary, adapters, and consumers at the edges of existing domains; none adds a new kind of physics. The test for every future capability is the one the platform already lives by: *adding it must be an act of description, not an act of surgery.*

**Portfolio Platform → Investment Intelligence** *(complete).* This transition built the stack itself: deterministic truth, derived knowledge, disciplined judgment, independent evaluation. It is listed because it proved the pattern: evaluation was added without touching the optimizer; execution intelligence was added without touching accounting. The architecture described here is not a proposal — it is the generalization of transitions that already succeeded.

**Investment Intelligence → Multi-Asset Platform** *(current).* The Asset Registry — identity as a permanent, defended fact — was this era's keystone, and it is now in place. What remains is description: each new asset class arrives as an Asset Foundation definition (behavior, classification, lifecycle vocabulary), a Market Intelligence valuation source, and a Ledger vocabulary extension for its flows. The engines that replay a stock ledger replay a gold ledger; the formulas that measure an equity portfolio measure a mixed one. If any asset class requires editing an engine, the failure is in the abstraction, and the abstraction — not the engine — is what gets fixed.

**Multi-Asset Platform → Wealth Platform.** Two expansions, both already homed: Connectivity & Ingestion grows doors (institutions, statements, feeds) until the platform can absorb a whole financial life without manual transcription; Wealth Intelligence grows vocabulary (goals, net worth, cash flow, obligations, protection) over the same ledger discipline. A mortgage payment and a dividend are both ledger events with provenance. Nothing below the Knowledge layer changes at all.

**Wealth Platform → AI Wealth Advisor.** The horizon — and, architecturally, the *smallest* transition, because everything hard about it is a prerequisite the platform will already have. An advisor that knows a person's full financial picture, explains it in their language, and advises with an auditable track record requires: deterministic accounting (so advice rests on true numbers), immutable decision records (so the track record cannot be flattered), independent evaluation (so trust is measured, not asserted), and human sovereignty (so autonomy is delegated, never assumed). Those are Laws 1–15, already in force. The advisor is not a new platform. It is the Experience and Decision layers growing more fluent, with more of the world plugged into the edges — and the same constitution underneath.

The pattern across all four transitions is the same, and it is the reason this document can claim longevity: **the domains are defined by questions, not by features.** "What is this thing?", "what is it worth?", "what happened?", "what does it mean?", "what should be done?", "was the advice right?", "how does a person meet it?" — these questions are as valid for a retirement plan as for a stock trade. Features answer the questions differently over time; the questions, and the boundaries between them, do not move.

---

## 10. Amendment

This document changes the way constitutions change: rarely, explicitly, and with its reasoning recorded.

- A change to Section 4 (Laws) or Section 7 (Relationships) is a constitutional amendment: the document is amended *first*, the reasoning is recorded in [DECISION_LOG.md](../engineering/DECISION_LOG.md), and only then does the system change. Never by drift, never by increment, never by temporary exception.
- A change to domain boundaries (Section 6) is a major event and follows the same process.
- Clarifications that change no meaning may be made freely; when in doubt, it is an amendment.
- Where a domain has its own constitution ([OPTIMIZER_PHILOSOPHY.md](../investment/OPTIMIZER_PHILOSOPHY.md) for Decision Intelligence; [PORTFOLIO_CALCULATION_RULES.md](../investment/PORTFOLIO_CALCULATION_RULES.md) for the canonical accounting semantics), that document governs inside the boundary and this one governs the boundary itself. A conflict between them is reconciled explicitly, not resolved by whichever document was read last.

---

## 11. Architecture Governance

_Added in Constitution v1.1. This section defines the precedence hierarchy among the platform's written artifacts. It adds no new law; it states how the existing laws bind the rest of the record._

The platform's written record spans six levels of authority. Each level speaks in more detail, and changes more freely, than the level above it:

```
1. Platform Architecture          this document — purpose, laws, domains, boundaries
        ↓
2. Domain Constitutions           the interior law of one domain
                                  (OPTIMIZER_PHILOSOPHY.md for Decision Intelligence;
                                   PORTFOLIO_CALCULATION_RULES.md for accounting semantics;
                                   future domains may ratify their own)
        ↓
3. Architecture Decision Records  binding point rulings on specific questions
                                  (docs/decisions/ and DECISION_LOG.md)
        ↓
4. Technical Design Documents     domain models, integration guides, implementation plans
        ↓
5. Implementation Documentation   the system as built and when it changes
                                  (ARCHITECTURE.md, ROADMAP.md)
        ↓
6. Source Code                    the current realization of everything above
```

The rules of precedence:

**G1 — Higher states intent; lower states reality.** When two levels appear to disagree, the higher one says where the platform is going and the lower one says where it is today. That gap is a roadmap item, not a contradiction — *unless* the lower artifact asserts a different intent, in which case rule G4 applies.

**G2 — Lower may refine, never weaken.** A lower-level artifact may add constraint, precision, and detail within what the levels above permit. It may never relax a law, reinterpret a boundary, or carve an exception. An exception that deserves to exist deserves to be an amendment at the level that owns the rule.

**G3 — Silence delegates.** Where a higher level is silent, the decision belongs to the highest level that speaks. Deciding something the constitution never addressed is normal work, not an amendment — but the decision is recorded at its proper level, so that silence above remains deliberate rather than accidental.

**G4 — Conflict is a defect, resolved upward.** A genuine conflict of intent between levels is never resolved by recency, by the seniority of an author, or by pointing at running code. Either the lower artifact is brought into conformance, or the higher one is amended through its own process — and the reconciliation is recorded.

**G5 — Each level amends by its own mechanism.** Levels 1–2 follow the constitutional process (Section 10). Level 3 rulings are immutable once made: a wrong ADR is superseded by a new ADR that names it, never edited in place — Law 2, applied to the platform's record of itself. Levels 4–5 are revised freely and owe the reader currency, not permanence. Level 6 changes constantly.

**G6 — Code is never precedent.** The existence of an implementation is evidence of what *is*, never an argument for what *should be*. "The code already does X" is a level-6 statement of reality; it carries no authority over levels 1–4, and an invariant is never considered amended because an implementation drifted from it.

The scope boundary stated in Section 10 remains as ratified: a Domain Constitution is supreme *inside* its domain and subordinate to this document *at* the boundary. This section adds only the levels below them.

---

## 12. Canonical Vocabulary

_Added in Constitution v1.1._

The platform maintains exactly one vocabulary document: [GLOSSARY.md](../GLOSSARY.md). It is hereby designated the **canonical vocabulary** — Law 9 applied to language. A platform that lets the same word mean different things in different documents will eventually let the same word mean different things in different engines.

The rules:

**V1 — One term, one meaning, one home.** Every platform noun is defined once, in the glossary. Every other document — at every governance level — uses the term and links to it; none redefines it. Two documents needing different meanings for one word is a naming defect, and one of them renames.

**V2 — New nouns are registered before they are relied upon.** A document that introduces a term defines it once, precisely, and registers it in the glossary in the same change. An unregistered term of art is a private dialect, and private dialects are where boundary leaks begin.

**V3 — Constitutional terms carry constitutional weight.** The names of the nine domains, the six layers, the three gates, and the load-bearing vocabulary of the laws (*witness*, *authority*, *provenance*, *proposal*, *derivation*, *canonical event*, *observer plane*) are reserved: they may not be reused for anything else, and a glossary edit that changes what one of them *means* is an amendment of this document under Section 10, not a dictionary update. Glossary edits that add terms, add clarity, or fix errors in non-reserved entries are ordinary maintenance.

**V4 — The vocabulary serves every level.** The glossary is not itself a governance level; it is the shared language all six levels are written in. Precedence disputes are settled by Section 11; meaning disputes are settled here.

---

## Related Documents

- [README.md](README.md) — the Architecture Handbook: reading order and document map
- [PLATFORM_EVOLUTION.md](PLATFORM_EVOLUTION.md) — the manifesto: why this era, the evolution strategy, and the maintainer's test
- [OPTIMIZER_PHILOSOPHY.md](../investment/OPTIMIZER_PHILOSOPHY.md) — the constitution of Decision Intelligence
- [PORTFOLIO_CALCULATION_RULES.md](../investment/PORTFOLIO_CALCULATION_RULES.md) — frozen accounting semantics
- [ENGINEERING_PRINCIPLES.md](../engineering/ENGINEERING_PRINCIPLES.md) — code-level principles
- [DECISION_LOG.md](../engineering/DECISION_LOG.md) — the record of why
- [ARCHITECTURE.md](ARCHITECTURE.md) — the system as built today
- [ROADMAP.md](ROADMAP.md) — when the gaps close
- [../GLOSSARY.md](../GLOSSARY.md) — shared vocabulary
