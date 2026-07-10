Principal Product Architect Review: Platform Domain Architecture
TL;DR: The draft is a reasonable feature inventory, but it has three structural flaws: it makes your most valuable asset (the ledger) invisible, it has no domain for the actual frontier of the next 3–5 years (getting the outside world into the platform), and it organizes one domain by technology ("AI") rather than by purpose — which puts decision-making and the thing that judges decision-making under one roof, weakening an invariant your own constitution calls permanent. I propose a nine-domain architecture that mirrors your layer stack, where the taxonomy itself encodes the platform's rules.

1. Critique of the Draft
Flaw 1 — The ground truth is missing
There is no domain for the Transaction ledger, replay, validation, repair, or accounting correctness. "Holdings" appears under Portfolio Intelligence as if holdings were a primary object — but per ADR-001 and Platform Evolution invariant #1, holdings are a derivation of ledger events. This isn't pedantry: the ledger discipline is the single most expensive, most defended asset the platform owns (an entire hardening era, five ADRs, the rebuild/validator/repair machinery). A product taxonomy that doesn't name it will, over 3–5 years, treat it as an implementation detail — and implementation details get "optimized." It is also genuinely product: imports, corrections, reconciliation, provenance, and audit trails are user-facing capabilities, especially once multi-broker arrives.

Flaw 2 — No ingestion domain, yet ingestion is the frontier
Platform Evolution §1 says it plainly: correctness stopped being the frontier; the hard problems are now at the edges. The multi-asset, whole-wealth ambition lives or dies on the Universal Input Layer — broker imports, statements, bank feeds, reconciliation, review queues, provenance. The draft has no home for any of it. This is the most consequential omission: a taxonomy signals where investment goes, and this one signals zero investment in the thing that unlocks everything in "Wealth Intelligence."

Flaw 3 — No market data domain
"What things are worth" — prices, history, calendars, FX, provider independence — is a first-class layer in your own architecture manifesto and a named Phase 3 roadmap item (multiple price providers, market calendar). In the draft it's nowhere, presumably smeared across Asset Intelligence's "Metadata." Asset identity ("what it is") and asset valuation ("what it's worth") are different domains with different change cadences and different failure modes; conflating them recreates the exact provider-coupling the manifesto forbids.

Flaw 4 — "AI Intelligence" organizes by technology, not purpose
AI is an ingredient, not a domain. Within five years every domain will have AI in it — the regime detector, the news pipeline, the wealth advisor, even ingestion (statement parsing). Naming a domain "AI Intelligence" gives it a gravitational pull: every AI-flavored capability will get filed there regardless of what it's for, and the domain becomes a junk drawer. The capabilities currently listed there are really Decision Intelligence (Analyzer, Optimizer, Recommendation — which are also partially the same thing: a recommendation is the optimizer's output, not its sibling).

Flaw 5 — Evaluation must not live with the thing it evaluates
Your constitution's most repeated invariant: evaluation observes; it never touches (Platform Evolution invariant #5, Optimizer Philosophy §12). Putting Evaluation inside the same domain as Optimizer and Recommendation puts the judge on the defendant's payroll. Over years, domain-internal convenience erodes boundaries — shared roadmaps, shared owners, shared "quick" couplings. The separation should be encoded in the product structure itself: a Trust & Evaluation domain that consumes Decision Intelligence's records and owes it nothing.

Flaw 6 — Explainability is a duty, not a module
Invariant #10 calls explainability a fiduciary duty of every number and every recommendation. Listing it as one capability among five implies it's a feature you build once. It should disappear from the tree and reappear as a cross-cutting obligation every domain carries — the same way "correctness" isn't a module.

Flaw 7 — Rebalancing under Portfolio Intelligence invites the cardinal sin
The optimizer is the rebalancer — Belief Engine plus Execution Optimization plus Execution Plan. A separate "Rebalancing" capability under a different domain is an open invitation for a second implementation of what OPTIMIZER_PHILOSOPHY.md already governs (the "parallel implementations are the cardinal sin" rule, ADR-004). Rebalancing belongs in Decision Intelligence, or rather — it already exists there under its real names.

Flaw 8 — Attribution is missing entirely
BHB attribution, regime attribution, factor exposure, human-vs-AI, opportunity cost — this is among the most differentiated capability sets you've shipped, and the draft doesn't contain the word. Meanwhile "Metadata" (a property of the Registry, not a capability) and "Cross Asset" (ambiguous between identity linkage and analytics) get top billing under Asset Intelligence.

Flaw 9 — Wealth Intelligence mixes abstraction levels
"Retirement" is a type of goal, not a peer of "Goals." "Cash" is already a ledger concept — cash balances, deposits, withdrawals exist today under accounting; what Wealth adds is cash-flow planning (income, expenses, budgets). "Tax" as listed conflates tax planning (wealth) with tax recording (fees/VAT already in the ledger). The domain needs restructuring around Phase 5's actual shape: net worth, planning, protection.

Flaw 10 — Platform is too thin for the stated ambition
Dashboard, Notification, Timeline, Settings. If SaaS (Phase 4) is real within this taxonomy's lifetime, there is a whole missing operational surface: identity/workspaces, entitlements, audit, billing. And there is no home at all for the AI Experience layer — daily briefs, natural-language portfolio review, copilot — which your own layer stack treats as distinct from Decision Intelligence and which is the entire Phase 6 horizon. "Timeline," meanwhile, is not a platform widget; it's a cross-domain view over the ledger, decisions, and evaluations.

2. The Reorganized Architecture
The organizing principle: the taxonomy should mirror the layer stack, because truth flows up. Read top to bottom as a sentence: what things are → what they're worth → what happened → how facts enter → what it means → what to do → whether to trust it → your whole financial life → how a human experiences it.

Legend — Tier: F Foundation · CI Core Intelligence · AI² Advanced Intelligence · FV Future Vision. Horizon: Now Current · Near Near Future · Far Future. ⚑ = made possible (or made honest) by the Asset Registry.


Investment Intelligence Platform

├── 1. Asset Foundation — what things ARE
├── 2. Market Intelligence — what things are WORTH, and the world around them
├── 3. Ledger & Accounting — what you DID (the ground truth)
├── 4. Connectivity & Ingestion — how facts ENTER (many doors, one hallway)
├── 5. Portfolio Intelligence — what the truth MEANS
├── 6. Decision Intelligence — what to DO about it
├── 7. Trust & Evaluation — whether the advice WAS RIGHT
├── 8. Wealth Intelligence — the whole financial LIFE
└── 9. Experience & Platform Operations — how humans MEET all of it
Domain 1: Asset Foundation
Capability	Tier	Horizon	
Asset Registry (permanent identity)	F	Now	the anchor
Classification (sector/region/type dimensions)	F	Now	⚑
Cross-Asset Identity (DR ↔ underlying, spelling variants, adjudication)	F	Now	⚑
Asset Definitions (behavior plugins: units, valuation cadence, fee/tax texture)	F	Near	⚑
Corporate Actions & Lifecycle (splits, renames, delistings as identity facts)	F	Near	⚑
Asset Search & Discovery	CI	Near	⚑
Renames from the draft: "Metadata" dissolves into Registry + Classification (it was a property, not a capability). "Templates" becomes Asset Definitions — the "assets are plugins" library, which is the real name of the multi-asset strategy. "Cross Asset" splits: identity linkage stays here; cross-asset analytics moves to Portfolio Intelligence.

Domain 2: Market Intelligence
Capability	Tier	Horizon	
Prices & History (provider-agnostic)	F	Now → Near	⚑ multi-provider
Market Calendars & FX	F	Near	
Regime Detection	CI	Now	
News & Event Intelligence	CI	Now (sentiment) → Far (event understanding)	
Macro Context (rates, inflation, cycles)	AI²	Far	
Alternative Data	FV	Far	
New domain. Regime detection moves here from analytics limbo — it's a statement about the market, not about a portfolio. Everything here is evidence for beliefs, consumed by Decision Intelligence, never a bypass around it.

Domain 3: Ledger & Accounting
Capability	Tier	Horizon
Transaction Ledger (single source of truth)	F	Now
Replay & Reconstruction	F	Now
Validation & Repair	F	Now
Cost Basis, Cash, Fees & NAV Conservation	F	Now
Snapshots & Historical State	F	Now
Provenance & Confidence (origin of every event)	F	Near
The domain the draft forgot. Everything here is Current and permanent-core — it appears in the taxonomy not because it needs building but because it needs defending, and because provenance (the one Near item) is the prerequisite for Domain 4.

Domain 4: Connectivity & Ingestion
Capability	Tier	Horizon	
Manual Entry	F	Now	
File Import (broker CSV, statements)	CI	Near	⚑
Review & Reconciliation Queue (proposals, never silent writes)	CI	Near	⚑
Broker & Bank Connections	AI²	Far	⚑
Multi-Broker Portfolio Unification	AI²	Far	⚑
Corporate-Action & Dividend Feeds	AI²	Far	⚑
Document Understanding (PDF/OCR statement parsing)	FV	Far	
The strategic frontier, promoted to a named domain. Its governing rule is already written (Platform Evolution §5): every door produces canonical ledger events; nothing bypasses the hallway; the human confirms truth.

Domain 5: Portfolio Intelligence
Capability	Tier	Horizon	
Holdings & Valuation (derived, multi-asset)	CI	Now	⚑ multi-asset
Performance & Returns (canonical formulas)	CI	Now	
Attribution (BHB, regime, factor, opportunity cost)	AI²	Now	
Risk & Exposure (concentration, factor, drawdown)	CI	Now	
Allocation & Cross-Asset Analytics	CI	Now → Near	⚑
Benchmarking	CI	Now	
Household / Multi-Portfolio Aggregation	AI²	Near	⚑
"Rebalancing" leaves (→ Domain 6). "Holdings" stays only as the derived, valued view — the truth lives in Domain 3. Attribution enters, finally named.

Domain 6: Decision Intelligence
Governed, as today, by OPTIMIZER_PHILOSOPHY.md.

Capability	Tier	Horizon
Analysis & Signals (per-asset TA/FA/news beliefs)	CI	Now
Belief Engine (three-layer optimizer, consensus)	CI	Now
Policy & Constraint Governance (regime constraints, envelopes, personas)	CI	Now
Execution Intelligence (funding, sizing, timing, execution plans)	AI²	Now
Idea Intake (human ideas, committee review)	CI	Now
Scenario Simulation ("what if")	AI²	Near
Goal-Aware & Tax-Aware Recommendations	FV	Far
The draft's "Analyzer / Optimizer / Recommendation" trio collapses into its real structure: analysis produces beliefs, the belief engine produces recommendations, execution intelligence turns them into plans. Rebalancing is this domain — it needs no separate name.

Domain 7: Trust & Evaluation
Deliberately a separate domain from 6 — the judge does not share an office with the defendant.

Capability	Tier	Horizon	
Decision & Recommendation Records (immutable)	F	Now	⚑ record integrity
Shadow Portfolios (the paths not taken)	AI²	Now	
Grading (plan, horizon, report cards)	AI²	Now	⚑
Human vs. AI Benchmark	AI²	Now	
Confidence Calibration	AI²	Now	
Trust Report	AI²	Now	
Learning Engine (calibration → adaptation, via governed config only)	FV	Far	
This is the platform's genuinely rare capability set — most competitors make recommendations; almost none maintain an auditable, immutable track record of whether their recommendations were right. Elevating it to a domain is also a market position.

Domain 8: Wealth Intelligence
Capability	Tier	Horizon	
Goals & Goal Discovery	CI	Now	(the goal wizard exists)
Net Worth (everything ownable, one view)	AI²	Near → Far	⚑
Cash-Flow Planning (income, expenses, budget, emergency fund)	AI²	Far	
Life Goals as Plans (retirement, FIRE, education, house — types of goal, not domains)	AI²	Far	
Tax Planning	FV	Far	
Debt & Protection (insurance, estate)	FV	Far	
Restructured so Retirement is a goal type under planning, "Cash" splits into ledger cash (Domain 3, exists) versus cash-flow planning (here), and tax splits into recording (Domain 3, exists) versus planning (here).

Domain 9: Experience & Platform Operations
Capability	Tier	Horizon
Dual-Mode Presentation (MUJI calm / Quant depth)	CI	Now
Dashboards & Operations Center	CI	Now
Unified Timeline (ledger + decisions + evaluations, one stream)	CI	Near
Notifications & Alerts	CI	Near
AI Experience (daily brief, natural-language review, copilot)	FV	Far
Settings & Governance Controls	F	Now
Multi-User, Workspaces, Entitlements, Billing, Audit	FV	Far
Explainability does not appear here or anywhere — it is a stated obligation of every capability in every domain, enforced at review, not shipped as a feature.

3. What the Asset Registry Just Unlocked
The honest framing: the Registry didn't add a feature, it added a precondition. Before it, the platform's unit of identity was a ticker string — and a ticker string cannot survive a rename, cannot equate a DR with its underlying, cannot deduplicate the same trade arriving from two brokers, and cannot describe a gold bar. Specifically, the Registry is what makes these credible rather than aspirational:

Multi-asset itself (Domains 1, 5, 8). "Assets are plugins" requires a place to plug them in. Asset Definitions attach behavior to a permanent identity; without the Registry, every new asset class would have been another suffix-parsing heuristic.
Multi-broker unification (Domain 4). Reconciling the same instrument across brokers under different spellings is an identity problem first. The match_known_symbols discipline — Registry verdict wins, conflicts never papered over, ambiguity surfaces for human adjudication — is exactly the reconciliation kernel the review queue will need.
Corporate actions and lifecycle (Domain 1). A split or rename can now be a fact attached to an identity that survives it, instead of an event that orphans history.
Provider independence (Domain 2). Mapping many provider symbologies onto one identity is what makes "no engine knows where a price came from" achievable rather than rhetorical.
Classification-consistent analytics (Domain 5). Sector/region/type exposure across asset classes requires one classification authority; Phase 7 consolidation just made the Registry that authority.
Evaluation that survives time (Domain 7). Recommendation records now carry resolved identity, so grades and track records remain joinable to reality even after symbols change — a track record keyed to ticker strings would silently rot.
Net worth (Domain 8). "Everything ownable, one view" presumes everything ownable has an identity. It now can.
Asset search and discovery (Domain 1). You can only search a catalog that exists.
4. The Three Decisions That Matter Most
If you take nothing else from this review:

Name the ledger and name ingestion as product domains. The draft's biggest risk isn't a wrong grouping — it's that the two things the next era depends on most (defending the ground truth, and building the doors into it) have no name, and unnamed things get no roadmap.
Split Decision Intelligence from Trust & Evaluation. Your constitution already demands the boundary; the product structure should make it impossible to forget.
Retire "AI Intelligence" as a category. Organize by what capabilities are for. AI is how half the platform works; it is not what any of it is for.