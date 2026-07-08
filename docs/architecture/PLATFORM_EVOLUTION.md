# Platform Evolution

_The long-term product and architecture vision for the Portfolio Intelligence Platform._
_This is a manifesto, not a specification. It defines direction, philosophy, and boundaries for the years after v2.0 — not milestones, schemas, or tasks._

_Read together with [OPTIMIZER_PHILOSOPHY.md](OPTIMIZER_PHILOSOPHY.md) (the constitution of the decision-making layers), [ENGINEERING_PRINCIPLES.md](ENGINEERING_PRINCIPLES.md) (how code is written), [ARCHITECTURE.md](ARCHITECTURE.md) (what exists today), and [DECISION_LOG.md](DECISION_LOG.md) (why it exists that way). Where those documents govern a subsystem, they continue to govern it. This document governs the space between subsystems — and the space where subsystems do not yet exist._

---

## 0. Preface: Why This Document Exists

v2.0 marked the end of an era. Foundation, Portfolio Engine, Replay Engine, Portfolio Metrics, Benchmark Engine, the Three-layer Optimizer, Execution Intelligence, AI Evaluation, and Accounting Correctness are complete, tested, and stable. The core investment engine works, and — more importantly — it is *known* to work: every number it produces can be replayed, validated, attributed, and explained.

The next era will be judged by a different standard. Not "does the engine compute the right number?" but "can the platform absorb a new asset class, a new data source, a new broker, a new input format — without anyone touching the engines that compute the right number?"

This document exists so that standard is written down before the first new capability arrives, not reverse-engineered after the third rewrite.

---

## 1. Why Platform Evolution?

### Why now is the right time

There is exactly one moment in a platform's life when generalization is cheap: immediately after the core is proven correct and before the second consumer of that core arrives. Generalize earlier, and you abstract over requirements you haven't met yet — abstraction by guesswork. Generalize later, and every engine has grown quiet assumptions about its one consumer, and each new asset class or data source pays the cost of unwinding them.

We are at that moment. The engines are correct, the invariants are documented, the test suites encode the accounting rules, and the platform still serves essentially one shape of input: Thai and US equities, priced by one provider, entered by one set of transaction endpoints. The assumptions are still visible. In two years of feature growth they will be buried.

### What changed after v2.0

Three things, and they change the nature of the work:

1. **Correctness stopped being the frontier.** Through v2.0, the hardest problems were internal: NAV conservation, deterministic replay, cash-flow-adjusted returns, ledger validation, the Belief/Execution separation. Those problems are solved and constitutionally protected. The hardest problems are now at the *edges* — what enters the platform and what the platform connects to.

2. **The engines became worth protecting.** Before v2.0, rewriting an engine was Tuesday. Now every engine carries accumulated correctness — decision-log entries, regression tests, repaired production incidents — that a rewrite would forfeit. The cost-benefit of "rewrite to extend" has permanently inverted.

3. **The roadmap's ambitions outgrew the input surface.** Phases 4–6 — SaaS, Personal Wealth Platform, AI Wealth Advisor — all presume the platform can hold a whole financial life: funds, gold, crypto, cash, property, statements from many brokers and banks. None of that is an analytics problem. All of it is a platform problem.

### Why development shifts from building engines to expanding the platform

Because the engines are no longer where value is created — they are where value is *kept*. A new analytics engine adds one capability. A platform that lets existing engines serve new assets, new inputs, and new integrations multiplies every capability we already have. The Replay Engine that replays a stock ledger should replay a gold ledger. The Metrics Engine that computes a stock portfolio's return should compute a mixed portfolio's return. The AI Evaluation layer that grades equity recommendations should grade any recommendation.

The shift is from **building intelligence** to **building the surface area that intelligence can reach.**

---

## 2. Platform Philosophy

Principles that bind every future feature, in every layer, regardless of which phase or era it ships in.

1. **Correctness before intelligence.** No AI capability, integration, or convenience ships at the cost of accounting correctness. A wrong number explained beautifully is worse than a right number explained plainly. This was the founding principle; growth does not dilute it.

2. **Transactions remain the single source of truth.** Every asset the platform will ever hold — stock, fund, gold, crypto, property — exists in the system *because a ledger event says so*, and its state is derivable by replaying those events. Any column, cache, or snapshot is a disposable derivation. (ADR-001, extended to all future assets.)

3. **The Portfolio Engine remains deterministic.** Same ledger, same prices, same result — forever, for every asset class. Determinism is not an implementation detail; it is what makes validation, repair, audit, and trust possible.

4. **Replay remains reproducible.** Any historical state must be reconstructible from the ledger at any future date, regardless of how many new asset types and input sources have arrived since that history was written.

5. **AI never mutates accounting.** AI layers read derived state and produce beliefs, recommendations, and explanations. They never write to the ledger, never adjust a balance, never "correct" a number. The boundary between judgment and arithmetic (OPTIMIZER_PHILOSOPHY.md §6) is a platform-wide boundary, not an optimizer-local one.

6. **Evaluation never modifies historical truth.** Anything that grades, attributes, or learns consumes recorded objects and produces new ones. It never reaches upstream, never edits what it judges, never rewrites the past to flatter the present.

7. **Assets are plugins.** The core engines know what an *asset* is — something ownable, priceable, and transactable — not what a *stock* is. Everything stock-specific (symbols, exchanges, fee schedules, market hours, corporate actions) lives at the edge, in asset definitions the engines consume but do not contain.

8. **Data providers are interchangeable.** No engine may know where a price came from. Provider identity, quirks, delays, and formats are absorbed at the edge (the Yahoo Finance `.BK` lag is already a documented instance of why). Losing any single provider must never be an architectural event.

9. **Normalize at the boundary, never in the core.** Every input — manual entry, CSV, broker API, PDF, bank feed — is translated into canonical ledger events *before* it reaches the Portfolio Engine. The engines never contain a special case for where data came from. If the core needs an `if broker == ...`, the boundary has failed.

10. **One implementation per business rule.** Every calculation has exactly one authoritative implementation shared by all consumers (ADR-004). Platform growth multiplies consumers; it must never multiply implementations.

11. **Degradation is loud.** Every adapter, provider, and integration can fail; none may fail silently. A platform of many edges is a platform of many failure modes — observability of degraded modes is the price of having edges.

12. **The human owns the ledger.** Automated inputs *propose*; the recorded financial truth of a person's life is never silently written by a machine. Imports, syncs, and parsed statements enter through review, reconciliation, or explicitly granted, revocable delegation — never by default.

---

## 3. Platform Layers

The long-term conceptual architecture. Each layer speaks only to its neighbors, depends only downward, and trusts the layer below to have done its job. The layers are conceptual — they describe responsibility and dependency direction, not deployment or module structure.

```
Presentation
    what the user sees; dual-mode (MUJI calm / Quant depth); renders, never computes
        ↓
AI Experience
    conversation, briefs, copilot, translation of platform truth into human language
        ↓
Decision Intelligence
    beliefs, recommendations, execution planning, policy, evaluation, learning
    (governed by OPTIMIZER_PHILOSOPHY.md)
        ↓
Portfolio Intelligence
    metrics, attribution, benchmarks, risk, regime — derived analytics over portfolio truth
        ↓
Portfolio Engine
    replay, snapshots, validation, repair, reconstruction — deterministic state from the ledger
        ↓
Accounting Engine
    the ledger itself: transactions, cash, cost basis, NAV conservation — the platform's ground truth
        ↓
Universal Asset Platform
    what things ARE: asset definitions, identity, classification, lifecycle, corporate actions
        ↓
Market Data Platform
    what things are WORTH: prices, history, calendars, FX — provider-agnostic
        ↓
External Integrations
    the outside world: brokers, banks, data vendors, documents — adapters all the way down
```

Two rules give this stack its meaning:

**Truth flows up; nothing flows down.** Each layer derives from the layers beneath it and is consumed by the layers above it. The AI Experience layer cannot write a transaction. Decision Intelligence cannot adjust a price. Presentation cannot compute a return. When a higher layer needs something changed below, it goes through the boundary that owns it — a proposed ledger event, a review queue, a human decision.

**The middle is stable; the edges churn.** The Accounting and Portfolio Engines at the center change rarely and reluctantly. The outermost layers — Integrations, Presentation — change constantly and cheaply. The gradient of change-frequency from edge to core is the architecture. A design that requires a core change to accommodate an edge event is, by that fact alone, wrong.

---

## 4. Universal Asset Vision

Today the platform holds equities. Tomorrow it should hold anything a person can own: stocks, ETFs, mutual funds, gold, crypto, bonds, cash in multiple currencies, property — and asset classes not yet invented.

The vision is **not** an engine per asset class. It is one set of engines and a growing library of asset definitions.

### What the core engines actually need

Strip away everything stock-specific, and the engines' real requirements are small. An asset is something that:

- can be **owned** in some quantity (shares, units, grams, coins, deeds — a number),
- can be **valued** (a price, a valuation, an appraisal — some source of worth over time),
- can be **transacted** (acquired, disposed, and adjusted through ledger events),
- may **generate flows** (dividends, interest, rent, staking rewards — cash the ledger records).

Replay, NAV conservation, cost basis, cash-flow-adjusted returns, snapshots, validation, repair — all of it already operates on those four properties. That is the whole point: the accounting rules hardened through v2.0 are *already* asset-agnostic in substance. Evolution means making them asset-agnostic in form, so the engines consume asset *behavior* instead of asset *type*.

### What varies per asset lives in the definition, not the engine

Each asset class brings its own texture: valuation cadence (a stock ticks by the minute; a property revalues yearly), unit semantics (fractional fund units, indivisible deeds), fee and tax structure, corporate-action vocabulary (splits and spin-offs for stocks; NAV distributions for funds; forks for crypto), market calendars, and identity conventions. All of that is *asset definition* — the plugin. None of it is *engine*.

The test for every future asset class is the same: **adding it must be an act of description, not an act of surgery.** If gold requires editing the Replay Engine, the abstraction has failed and the abstraction — not the engine — is what gets fixed.

### Honest boundaries of the vision

Some assets will stretch the model — a property with no daily price, a bond with accrual semantics, a currency that is simultaneously an asset and the unit of account. The commitment is not that every asset is trivial; it is that every asset's complexity is absorbed in its definition and its input adapters, and the invariants (Section 9) hold regardless. An asset that genuinely cannot satisfy the four properties above is not an asset the platform holds — it is a feature request against this document.

---

## 5. Universal Input Layer

Every fact the platform knows arrived from somewhere. Today, almost everything arrives through manual entry. Tomorrow: CSV exports, broker APIs, PDF statements, OCR of paper documents, banking feeds, corporate-action streams, dividend and interest notifications — and sources not yet imagined.

The vision is a single principle applied uniformly: **many doors, one hallway.**

### Many doors

Each input source gets its own adapter, fluent in that source's dialect — a broker's export format, a bank's feed protocol, the layout of a fund statement, the imprecision of OCR. Adapters are expected to be numerous, messy, source-specific, and frequently revised. That is their job: to contain the outside world's chaos at the boundary.

### One hallway

Every adapter, without exception, produces the same thing: **canonical ledger events** — the same transaction vocabulary the platform already trusts, extended over time to cover new flow types (interest, rent, staking, fees of new shapes). By the time input reaches the Accounting Engine, its origin is irrelevant and invisible. A BUY is a BUY whether it was typed by hand, parsed from a PDF, or streamed from a broker API.

This is why the engines survive integration growth untouched: they only ever see the hallway, never the doors.

### The standards every input source must meet

- **Provenance is preserved.** Every ingested event records where it came from, when, and through what adapter. When a number looks wrong three years later, the trail back to its source document must exist.
- **Confidence is explicit.** A hand-typed transaction, an API-confirmed fill, and an OCR guess are not equally trustworthy, and the platform must never pretend they are. Uncertain input is flagged as uncertain until confirmed.
- **The human confirms truth.** Automated inputs land as *proposals* subject to review and reconciliation — the ledger validation and repair machinery built in Phase 6 is the natural gatekeeper. Auto-acceptance is possible only as explicit, revocable delegation, per source, granted by the user. (This mirrors the autonomy rule of OPTIMIZER_PHILOSOPHY.md §16: delegated, never eroded.)
- **Duplicates and conflicts are boundary problems.** When the same trade arrives from a CSV and later from a broker API, deduplication happens in the input layer with its provenance data — never as a compensating heuristic inside metrics or replay (ADR-002 already forbids that, and it stays forbidden).
- **Nothing bypasses the hallway.** No integration, however trusted, writes portfolio state directly. Everything becomes ledger events first, or it does not enter.

---

## 6. Platform Boundaries

Growth is safe only if it is uneven — some parts of the platform must churn weekly while others barely change in a decade. Declaring which is which, in advance, is this section's job.

### The permanent core — stable, redesign-resistant, changed only with constitutional care

| Component | Why it must not move |
|---|---|
| **Accounting Engine** (ledger, cash, cost basis, NAV conservation) | It is the ground truth everything else derives from. Every change here re-opens every number the platform has ever produced. |
| **Replay Engine** | Reproducibility of history is a promise made to the past. A replay engine that changes behavior breaks every audit trail retroactively. |
| **Portfolio Metrics** (canonical return formulas, `compute_period_metrics`) | One implementation, frozen semantics, documented in PORTFOLIO_CALCULATION_RULES.md. New assets add inputs to these formulas; they never fork them. |
| **Ledger Validation & Repair** | The immune system. It must remain read-only in detection, explicit in repair, and independent of whatever it validates. |
| **AI Evaluation & Attribution** | Historical judgments and grades are records. The machinery that produces them may improve, but recorded evaluations are immutable and the evaluate-never-mutate boundary is permanent. |
| **The decision-layer constitution** (Belief/Execution separation, objective hierarchy) | Governed by OPTIMIZER_PHILOSOPHY.md; reaffirmed here as core. |

Changes to this core follow the constitutional process: amend the governing document first, record the reasoning in DECISION_LOG.md, then change the code. Never by drift.

### The evolving edge — expected to change frequently and cheaply

- **Input adapters and integrations** — new brokers, banks, formats; revised constantly as the outside world changes.
- **Market data providers** — added, replaced, and blended as coverage needs grow.
- **Asset definitions** — a growing library, each addition routine.
- **Presentation and AI Experience** — UI, conversation, briefs, translation layers; the fastest-moving surface in the platform.
- **Analytics on top of the metrics core** — new derived measures, attribution dimensions, and risk views, provided they consume the canonical metrics rather than re-deriving them.
- **AI models and prompts** — model generations will turn over many times within this document's lifetime; the platform must treat that as maintenance, not architecture.

### The membrane between them

The interesting work of the next era happens at the boundary: the contracts by which the edge talks to the core. Those contracts — canonical ledger events, asset definitions, provider-agnostic price interfaces — should change *slowly and additively*: new event types, new asset behaviors, new fields, yes; breaking redefinitions of existing meaning, essentially never. A contract that must break to admit a new capability was a contract designed too narrowly, and the lesson goes into the decision log.

---

## 7. Evolution Strategy

How capabilities get added for the next several years, stated as a preference order.

### The preferred path, always

```
New capability
    ↓
New adapter / new asset definition / new consumer of recorded objects
    ↓
Existing engine, untouched
```

### The forbidden path

```
New capability
    ↓
"The engine almost does this, let me just..."
    ↓
Rewritten engine, forfeited correctness, re-litigated invariants
```

### The strategy, in rules

1. **Extend by addition, not modification.** The first question for every new capability is: *which existing engine already owns this responsibility, and what adapter lets it serve the new case?* (This is ENGINEERING_PRINCIPLES.md "Reuse Before Create," promoted from code-level habit to platform-level law.)

2. **When the engine can't serve the new case, fix the abstraction, not the instance.** If the Replay Engine can't replay a fund ledger, the answer is never a `FundReplayEngine`. It is a deliberate, minimal generalization of the one Replay Engine — constitutionally reviewed, decision-logged, verified against the existing test corpus before the new asset ships.

3. **Parallel implementations are the cardinal sin.** The v2.0 hardening sprint exists in memory precisely because three engines once computed nine return fields three subtly different ways. Platform growth multiplies the temptation; ADR-004 stands: one rule, one implementation, all consumers.

4. **New stages are argued openly or not at all.** If a capability genuinely needs a new layer or pipeline stage — not an adapter, not an extension — it is added explicitly, in the governing document, with its responsibility and reason stated, exactly as OPTIMIZER_PHILOSOPHY.md §16 requires for the decision pipeline. Capabilities that smear across layers are redesigned.

5. **Every capability ships with its degraded mode designed.** Adapters fail, providers rate-limit, feeds lag. A capability is not done when it works; it is done when its failure is observable, contained at the edge, and non-corrupting to the core.

6. **Correctness debt is paid before capability is added on top of it.** When extending a subsystem exposes an existing gap (as position import, cash-flow contamination, and quantity corrections each did), the gap is fixed and decision-logged first. Building new floors on a known crack is how platforms die slowly.

---

## 8. Future Opportunities

Where the platform can go once the evolution above is real. These are directions, not commitments, and emphatically not milestones. Each is listed with the platform property that unlocks it — because that is the point: **every one of these is cheap if the platform evolves correctly, and a rewrite if it doesn't.**

**Multi-broker support.** Many brokers, one portfolio truth. Unlocked by the Universal Input Layer: each broker is one more adapter producing canonical events with provenance. Reconciliation across brokers becomes a ledger-validation feature, not a new subsystem.

**Universal Asset Registry.** A first-class catalog of everything ownable — identity, classification, lifecycle, corporate-action history — shared by every engine and every layer. Unlocked by "assets are plugins"; this is the plugin library grown into an institution.

**Alternative data.** Positioning data, flows, on-chain metrics, satellite-anything. Unlocked by the provider-agnostic Market Data Platform: alternative data is just more data with a different adapter and an honest confidence label.

**Macro data.** Rates, inflation, currency, cycles — context the regime detector already gestures at, generalized. Feeds Decision Intelligence as *evidence for beliefs*, never as a bypass around the deterministic layers.

**News intelligence.** From per-stock news sentiment (which exists) toward event understanding: what happened, to which assets, with what plausible mechanism. Lives strictly in the belief-formation layer; graded like every other signal by AI Evaluation.

**Learning Engine.** The platform already records every recommendation, decision, outcome, and grade immutably. A learning layer consumes that record to calibrate confidence, weight strategies, and adapt to regimes — the roadmap's Phase 6. Its constitutional constraint is inherited, not new: learning consumes records and produces new parameters through the governed configuration path; it never mutates history and never edits the thing it learned from.

**Personal Wealth Platform.** The roadmap's Phase 5: net worth, income, expenses, budgets, goals, debts, insurance — a whole financial life on the same ledger discipline. Unlocked by the Universal Asset vision plus the Input Layer: a mortgage payment and a dividend are both just ledger events with provenance.

**AI Wealth Advisor.** The horizon: a system that knows a person's full financial picture, explains it in their language, and advises with recorded, evaluated, accountable recommendations. Everything this platform has built is a prerequisite for doing that *responsibly* — deterministic accounting so the advice rests on true numbers, immutable decision records so the advisor's track record is auditable, evaluation infrastructure so trust is measured rather than asserted, and the human-decides principle so autonomy is delegated, never assumed. The advisor is not a new platform. It is this platform, with more of the world plugged into its edges.

---

## 9. What Should Never Change

The invariants. Everything else in this document is direction; this section is law. Any future change that violates one of these is wrong by definition, whatever its benchmark, demo, or roadmap pressure says. Deliberately breaking one requires amending this document first, with reasoning recorded in DECISION_LOG.md — never by drift, never by increment, never by "temporary" exception.

1. **The Transaction ledger is the single source of truth.** Every balance, holding, snapshot, and metric — for every asset class, forever — is a derivation of ledger events. No feature may create portfolio truth that does not live in the ledger.

2. **Recorded history is immutable.** Transactions, snapshots-as-computed, recommendations, decisions, evaluations, grades: once written, never edited. Corrections are new records with their own provenance. This platform's defining asset is a trustworthy past.

3. **Replay is deterministic and reproducible.** Same ledger, same price history, same rules → same state, on any machine, at any future date. No wall-clock dependence, no provider dependence, no randomness in the accounting path.

4. **Accounting is deterministic code; AI never writes it.** No model output, however capable the model, ever mutates a ledger, a balance, a cost basis, or a metric. The judgment/arithmetic boundary moves only by constitutional amendment.

5. **Evaluation observes; it never touches.** Anything that grades or attributes consumes recorded objects and produces new ones. An evaluation layer with write access to its subject is not an evaluation layer.

6. **Every business rule has exactly one implementation.** No engine, adapter, asset class, or convenience ever gets its own copy of a calculation that already has an owner.

7. **The core never knows the edge.** No engine may contain provider names, broker names, input-format logic, or asset-class special cases. If the core needs to know where something came from, the boundary has failed and the boundary gets fixed.

8. **Inputs are normalized before they become truth, and carry provenance forever.** Everything enters as canonical ledger events, tagged with origin and confidence. Nothing bypasses the hallway.

9. **Failures are loud.** No adapter, provider, engine, or AI layer degrades silently. Every fallback is observable. (ENGINEERING_PRINCIPLES.md, made perpetual.)

10. **Explainability is a fiduciary duty.** Every number is traceable to its inputs; every recommendation states its reason; every evaluation shows its evidence. As the platform grows toward a person's whole financial life, this duty grows with it — a system advising on someone's retirement owes *more* explanation, not less.

11. **The human owns their financial truth and their decisions.** The system advises, records, imports, and learns. It never silently writes the ledger, never silently executes, never erodes the decision point. Autonomy exists only as explicit, specific, revocable delegation.

12. **Correctness outranks everything.** Every conflict between a capability and a correct number resolves in favor of the number. This was true at the first commit. It is true at v2.0. It must be true at v10.

---

## For the Maintainer Reading This Years From Now

You are probably here because a new capability doesn't quite fit — a new asset that strains the definitions, an integration that wants to skip the hallway, a model that could "just handle" the accounting, a deadline that makes a second implementation look harmless.

The test is short:

- Does it write portfolio truth outside the ledger? → Stop.
- Does it edit recorded history? → Stop.
- Does it put provider, broker, or asset-class knowledge inside a core engine? → It's an adapter or an asset definition. Move it to the edge.
- Does it duplicate a calculation that has an owner? → Use the owner. Extend the owner if needed.
- Does it let AI touch accounting, or evaluation touch its subject? → Redesign it.
- Does it fail silently? → It isn't finished.
- Does it genuinely require breaking an invariant? → Then perhaps the invariant is wrong — that is allowed. Amend this document first, record why, and only then change the system.

The platform's engines took years and many hard-won corrections to make trustworthy. The purpose of everything written here is that they never have to be made trustworthy twice.

---

## Related Documents

- [OPTIMIZER_PHILOSOPHY.md](OPTIMIZER_PHILOSOPHY.md) — constitution of the decision-making layers
- [ENGINEERING_PRINCIPLES.md](ENGINEERING_PRINCIPLES.md) — code-level principles
- [ARCHITECTURE.md](ARCHITECTURE.md) — current system contracts
- [PORTFOLIO_CALCULATION_RULES.md](PORTFOLIO_CALCULATION_RULES.md) — frozen accounting semantics
- [DECISION_LOG.md](DECISION_LOG.md) — the record of why
- [ROADMAP.md](ROADMAP.md) — phase history and forward phases
