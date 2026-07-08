# Portfolio Domain Model

_The domain model of what a Portfolio **is**: a strategy, a policy, and an accounting boundary — not a bag of assets._

_This is not an implementation guide, not a database design, not an API specification. It defines what a Portfolio represents inside the platform, what it owns, how it is validated, and how it aggregates into a whole financial life — so that the Portfolio Engine stays deterministic while everything around it grows toward full wealth management._

_Read together with [PLATFORM_EVOLUTION.md](PLATFORM_EVOLUTION.md) (the layer stack and invariants), [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md) (what an Asset is — the object this document composes), [MARKET_DATA_PLATFORM.md](MARKET_DATA_PLATFORM.md) (how the outside world becomes canonical data), and [../investment/PORTFOLIO_CALCULATION_RULES.md](../investment/PORTFOLIO_CALCULATION_RULES.md) (the frozen accounting semantics that operate *inside* the boundary this document draws)._

---

## 1. Philosophy

### A Portfolio is not "a collection of assets"

A collection of assets is a *list*. Lists have no purpose, no rules, no history, and no opinion about what belongs in them. Nothing about a list explains why a holding is there, whether adding another one would be a mistake, what "doing well" means for it, or where its money came from.

A Portfolio, in this platform, is three things fused into one domain object:

1. **An investment strategy** — a purpose. "Aggressive Thai equity growth," "retirement income by 2045," "the emergency fund." The strategy is *why the portfolio exists*, and it is what makes every downstream judgment — a recommendation, a grade, a rebalance — meaningful. The platform already embodies this: a persona per portfolio, a goal profile per portfolio, an optimizer whose entire output is judged against *this portfolio's* intent, not portfolios in general.
2. **An investment policy** — the rules of engagement. What may be held, in which markets, in which currencies, with how much cash in reserve, under which constraints (§5). Policy is what turns strategy from a sentence into something enforceable *before* a transaction happens, rather than regrettable after.
3. **An accounting boundary** — a closed ledger. Every Portfolio owns exactly one transaction history, and that history fully determines its state by deterministic replay. Cash inside the boundary is this portfolio's cash; a return computed inside the boundary is attributable, reproducible, and uncontaminated by anything outside it. The boundary is what makes the number *mean something*.

Remove any leg and the object collapses: strategy without a boundary cannot be measured; a boundary without policy cannot be protected; policy without strategy is bureaucracy with no purpose. The platform's own history proves the fusion matters — the cash-flow-adjustment, imported-asset, and correction-stripping rules that took months to harden are all, at root, defenses of the *boundary*: guarantees that what crosses into a portfolio is classified truthfully so the strategy's performance can be judged honestly.

### Why Portfolio is a core domain object

The platform's conceptual chain now reads:

```
Asset            what a thing IS            (Universal Asset Architecture)
Asset Registry   who decides what it is
Market Data      what it is WORTH           (Market Data Platform)
Portfolio        what it is FOR             (this document)
```

Assets and prices are facts about the world; a Portfolio is a fact about *the investor* — the object where the world's instruments meet a person's intent. It is the unit of accounting (one ledger, one replay), the unit of strategy (one persona, one goal, one benchmark), the unit of evaluation (recommendations, grades, and human-vs-AI comparisons are all per-portfolio), and — as the platform grows toward wealth management — the composable unit from which a whole financial life is assembled (§7). Every engine the platform has built either operates *inside* a portfolio's boundary or *compares across* portfolio boundaries. There is no third mode, which is exactly what makes the object core.

---

## 2. Portfolio Responsibilities

### What a Portfolio owns

Ownership here means: the Portfolio is the authoritative scope for this concern, and the concern is meaningless without naming which portfolio it belongs to.

- **Holdings** — the current positions, always a *derived* view: holdings are what replaying the ledger says they are, never an independently edited list.
- **Transactions** — the ledger itself, the single source of truth (PLATFORM_EVOLUTION.md invariant 1), scoped entirely to this portfolio. A transaction belongs to exactly one portfolio; there is no shared or ambient transaction.
- **Replay** — the right to have its state deterministically reconstructed from its own ledger at any point in time. Replay never reaches across a portfolio boundary; that isolation is what makes it tractable and trustworthy.
- **Accounting** — cash balance, cost basis, realized and unrealized P/L, NAV — all computed within the boundary by the frozen rules of PORTFOLIO_CALCULATION_RULES.md.
- **Performance** — returns, cash-flow-adjusted and decomposed, meaningful precisely because the boundary controls what counts as external flow versus investment result.
- **Benchmark** — the standard this portfolio's strategy is judged against (§6). Benchmark is a property of the portfolio because it is a property of the *strategy*, and the strategy lives here.
- **Risk** — concentration, drawdown, volatility, policy compliance — assessed against *this portfolio's* policy and universe, not against a global notion of risk.
- **Analytics & evaluation scope** — attribution, recommendation history, decision records, shadow portfolios, AI grades: all keyed to the portfolio whose strategy they examine.

### What a Portfolio must never own

- **Asset identity.** A portfolio *references* `asset_id`s; it never defines, renames, or re-interprets an asset. Two portfolios holding the same asset hold the *same* asset (UNIVERSAL_ASSET_ARCHITECTURE.md §4).
- **Market data.** Prices, NAVs, FX, and calendars are canonical platform observations (MARKET_DATA_PLATFORM.md); a portfolio consumes them and may never maintain a private opinion of what something is worth.
- **Calculation rules.** The return formula, cash-flow definitions, and fee semantics are platform law with exactly one implementation (ADR-004). A portfolio parameterizes the rules (its currency, its window); it never gets its own variant.
- **Other portfolios' state.** No portfolio reads, funds, or adjusts another directly. Money moves between portfolios only as explicit, mirrored ledger events on both sides of both boundaries — the same discipline the platform applies to the outside world, applied internally.
- **The user's whole financial picture.** That is Wealth (§7), a level above. A portfolio that tries to answer "what is my net worth" has escaped its boundary.

---

## 3. Portfolio Identity

Identity here follows the same discipline the platform established for assets: a permanent internal identifier that business logic keys on, with everything human-facing layered above it as changeable description.

- **`portfolio_id`** — permanent, opaque, platform-assigned, never reused. Every ledger event, snapshot, recommendation, decision record, and grade keys on it. It survives renames, strategy changes, archival, and export, because history keyed to it must survive all of those.
- **Name** — the human label. Freely changeable; a rename is a cosmetic event with zero accounting or analytical consequence, which is only true *because* nothing downstream keys on the name.
- **Description** — the strategy in prose: what this portfolio is for, in the owner's words. Deliberately unstructured; the *structured* form of intent lives in universe (§4), policy (§5), persona, and goal profile.
- **Base Currency** — the currency in which this portfolio's NAV, returns, and benchmark comparisons are expressed. Every portfolio has exactly one; multi-currency *holdings* are welcome (the FX observations of MARKET_DATA_PLATFORM.md exist for this), but performance is always stated in one deliberate currency, chosen at creation, changed only as an explicit, recorded event — because silently reinterpreting the unit of account rewrites the meaning of every historical number.
- **Status** — where the portfolio is in its lifecycle (§8): active, archived, closed. Status gates what may happen *next*; it never touches what already happened.
- **Owner** — the person (or, in the platform's multi-user future, the principal) whose intent this portfolio expresses and whose authority governs its decisions. Ownership is an accountability fact: the human-in-the-loop of OPTIMIZER_PHILOSOPHY.md §13 is *this* person.
- **Workspace** — the containing context (§7). A portfolio lives in exactly one workspace; workspaces isolate wholly separate concerns (a personal life, a family member's finances, a future team account) from one another.
- **Lifecycle** — identity persists across every lifecycle transition. A closed portfolio is not a deleted portfolio; its `portfolio_id`, ledger, and history remain permanently addressable, because the platform's evaluation and attribution machinery is only honest if finished stories remain readable.

---

## 4. Investment Universe

*The most important design decision in this document.*

### The concept

An **Investment Universe** is a named, portfolio-level declaration of *what belongs in this portfolio* — the strategy's scope, made explicit and enforceable. Examples:

- **Thai Equity** — SET-listed stocks and their DR wrappers, THB-denominated.
- **US Equity** — US-listed stocks and ETFs.
- **Global Equity** — equities and equity ETFs across approved markets.
- **Retirement** — instruments eligible for the owner's retirement strategy, including tax-advantaged wrappers (RMF, SSF, Thai ESG) with their qualification rules in scope.
- **Fixed Income** — bonds, bond funds, cash-like instruments.
- **Crypto** — digital assets, on their own risk island by deliberate choice.
- **Multi-Asset** — a broad universe for genuinely mixed strategies.
- **Custom** — a user-defined scope for strategies the named universes don't anticipate.

A universe is *composed from* the vocabulary the platform already has — asset types, capabilities, markets, currencies (UNIVERSAL_ASSET_ARCHITECTURE.md §2, §5) — but it is a first-class named object, not an ad-hoc filter, because names carry intent: "this is my Retirement portfolio" is a statement about purpose that a list of asset-type checkboxes can never be.

### Why validation is driven by Universe, not Asset Type

Asset-type restriction answers the wrong question. "Is this a stock?" tells the platform nothing useful, because the honest validation question is always contextual: **"does this instrument belong in *this* portfolio?"** A US-listed ETF is a perfectly fine asset — and entirely wrong inside a Thai Equity retirement portfolio. A crypto asset is legitimate — and a category error in a fixed-income ladder. Asset type is a fact about the *instrument*; belonging is a fact about the *strategy*, and only the portfolio knows its strategy.

Type-driven validation also fails structurally, in exactly the way UNIVERSAL_ASSET_ARCHITECTURE.md §5 rejected for engines: it hardcodes today's taxonomy. A type whitelist written for stocks-and-ETFs must be *re-legislated* for every new asset class the platform absorbs, in every portfolio, forever. A universe, by contrast, is described in terms of markets, capabilities, and classifications — so when a new asset class arrives, existing universes either already admit it (a new SET-listed instrument enters "Thai Equity" automatically, correctly) or already exclude it (it doesn't match, correctly), with no redesign anywhere. Universe-driven validation is the portfolio-level expression of the platform's deepest extension rule: *described, not engineered*.

### How this prevents mistakes without preventing futures

The universe is a guardrail exactly where mistakes actually happen: at the moment of intent. A user about to buy a US stock inside their Thai retirement portfolio is stopped — not because the asset is invalid, not because the market is closed, but because *this portfolio declared that isn't what it's for*. That is a far more humane and more accurate error than any type check: it speaks the language of purpose, and it fires before money moves.

And because the universe belongs to the portfolio — not to the platform — flexibility costs nothing. The same user creates a second portfolio with a Global Equity universe and buys the same stock there, correctly. The rule was never "you can't hold this"; it was "you can't hold this *here*," which is precisely the boundary-keeping a multi-portfolio, multi-strategy platform owes its owner. Custom universes keep the escape hatch honest: a strategy nobody anticipated gets a declared scope, not an everything-goes free-for-all — because even "anything" should be a choice someone made explicitly.

---

## 5. Portfolio Policy

If the universe says *what belongs*, the policy says *how the portfolio is allowed to operate*. Policy is the portfolio-level rulebook — the structured constraints that validation (§9), the optimizer's constraint resolution, and execution planning all read from one place.

### The policy surface

- **Allowed Markets** — which venues this portfolio transacts in; usually implied by the universe, but independently tightenable (a Global Equity universe with "no emerging markets" is a policy choice layered on a universe choice).
- **Allowed Asset Classes** — a refinement within the universe (a Retirement universe that permits funds but not individual stocks).
- **Allowed Currencies** — which denominations may enter, and by extension how much FX exposure the strategy tolerates.
- **Fractional Trading** — whether this portfolio transacts in fractional quantities where the asset and venue support it (an asset capability and a portfolio permission are both required — two-sided, like every capability match in this platform).
- **Margin / Leverage** — whether borrowed exposure is permitted at all, and within what bounds. For most of this platform's portfolios the correct policy is a hard *no*, and the value of the policy is that the *no* is explicit, recorded, and enforced rather than assumed.
- **Cash Requirement** — the minimum cash reserve the strategy demands; already a live concept in the optimizer's cash-floor enforcement, promoted here to its proper home as portfolio policy.
- **Tax Rules** — the tax context this portfolio operates under, most importantly wrapper obligations: RMF holding-period rules, SSF windows, Thai ESG qualification. The policy doesn't *compute* taxes; it declares which regime's constraints validation and (future) tax-aware recommendations must respect.
- **Settlement Rules** — how strictly the portfolio models settlement timing: whether unsettled cash may fund new purchases, how conservatively pending flows are treated.

### Policy-driven validation

The architectural point is *where the rules live*, not how many there are. Every rule above could be — and in weaker systems is — scattered: some in UI checks, some in optimizer constants, some in an engineer's memory. This platform already learned the better pattern in its constraint-resolution work: overlapping rule sources merge deterministically into one effective envelope, and everything downstream reads the envelope. Portfolio Policy is that pattern made domain-level: **one declared rulebook per portfolio, consulted by everything, owned by nothing else.** Transaction validation reads it. The optimizer's constraint resolver merges it (as the "user settings" source it already models) with regime and system constraints. Execution planning respects it. Future features — tax-aware suggestions, goal-aware recommendations — read the *same* policy rather than growing their own.

Two disciplines keep policy honest. **Policy binds forward, never backward** — changing a policy changes what may happen next; it never re-judges recorded history, because history was valid under the policy of its day. And **policy is data, not code** — adding a policy dimension extends a vocabulary; it never adds an `if` to an engine (the same capability-over-branching rule, applied a third time).

---

## 6. Benchmark Model

A benchmark is the operational definition of "doing well" — and since every portfolio defines success differently, benchmark assignment must be per-portfolio, chosen to match the strategy, not inherited from a platform default.

### The benchmark forms

- **Single Benchmark** — one index or reference series. Right for single-market strategies: a Thai Equity portfolio against the SET index, a US Equity portfolio against a broad US index. Today's platform norm, and it remains the common case.
- **Composite Benchmark** — a weighted blend of reference series (60% equity index / 40% bond index, or a THB-equity + gold blend). Required the moment multi-asset portfolios exist, because judging a balanced strategy against a pure equity index systematically misreads both its bull-market "underperformance" and its bear-market "skill."
- **Policy Benchmark** — the composite derived from the portfolio's *own* declared target allocation: "what a passive investor with my policy weights would have earned." The most honest benchmark for strategy evaluation, because it isolates exactly what the platform's attribution machinery wants to isolate — the value of *decisions* over the value of *policy* — which is the same question the Ideal/Shadow portfolio infrastructure already asks from the recommendation side.
- **Category Benchmark** — the peer standard for a category of strategy (a retirement-fund category average, a fixed-income category). Right where an index would be misleading but "how do strategies like mine generally do" is answerable.
- **No Benchmark** — a legitimate, explicit choice, not a missing value. An emergency fund is not trying to beat anything; a property holding has no meaningful daily comparator. Declaring "this portfolio is not benchmarked" is truthful; defaulting it to an equity index would manufacture noise that every downstream consumer — alpha, attribution, AI grading — would then dutifully misinterpret.

### Why benchmark diversity is architecture, not preference

Every evaluation layer this platform has built — alpha, attribution, human-vs-AI comparison, recommendation grading, the Trust Report — is a comparison *against the benchmark*. If the benchmark mismatches the strategy, every one of those numbers is precisely computed and systematically wrong: the retirement portfolio looks like a failure in every rally, the crypto portfolio looks like a genius in every bubble, and the AI's graded track record inherits the distortion. Benchmark-per-portfolio is therefore not a display option; it is a *correctness requirement* of the evaluation stack. The benchmark also inherits the platform's data discipline for free: benchmark series are canonical observations (MARKET_DATA_PLATFORM.md §2, §7), and a missing benchmark degrades loudly as "uncomputable," never silently as "compared against something else" (§11 there). What a benchmark never does is influence accounting: NAV, returns, and cash are benchmark-blind — the benchmark judges the result; it never participates in producing it.

---

## 7. Wealth Hierarchy

```
Workspace
    the outermost context: one financial world, isolated from others
        ↓
Wealth
    one person's whole financial picture: the aggregation of everything they hold
        ↓
Portfolio
    one strategy, one policy, one accounting boundary
        ↓
Asset
    one instrument, canonically identified, held in some quantity
```

### Why Wealth is not a big Portfolio

The temptation is obvious: if a Portfolio holds assets, surely the whole net worth is just a bigger portfolio holding everything. The domain model rejects this, because the two objects differ in *kind*, not size:

- **A Portfolio has a strategy; Wealth has a shape.** A portfolio exists to pursue an intent and be judged against it. Wealth has no benchmark, no persona, no universe — it is not *trying* to do anything. It is the truthful sum of everything the person holds, across every strategy, including deliberate non-strategies like the emergency fund.
- **A Portfolio is an accounting boundary; Wealth is an aggregation *of* boundaries.** Wealth owns no ledger. Every transaction lives in exactly one portfolio; Wealth-level numbers are computed *from* portfolio-level truth, never recorded independently. This is the platform's single-source-of-truth discipline applied vertically: a Wealth layer with its own ledger would be a second source of truth for every baht in it, drifting from the portfolios the way derived columns drift from ledgers — a failure mode this platform has repaired often enough to have named rules against.
- **Portfolio performance is a judgment; Wealth analytics are a description.** "Did this strategy work?" is a portfolio question, benchmark-relative and attribution-laden. "What do I own, where, in what proportions?" is a Wealth question — descriptive, cross-cutting, benchmark-free (§10).

### Aggregation

Wealth-level views are always **derived, on demand, from portfolio replay** — net worth is the sum of portfolio NAVs converted into a common reporting currency at canonical FX; overall allocation is the union of holdings across boundaries, grouped by whatever dimension the question needs (asset class, market, currency, liquidity). Aggregation must also be *identity-aware*: the same `asset_id` held in three portfolios is one exposure worn three ways, and only the Registry's canonical identity (UNIVERSAL_ASSET_ARCHITECTURE.md §3) makes cross-portfolio exposure computable at all — one more reason business logic keys on `asset_id`, never on symbols. Workspace, above Wealth, is the isolation boundary rather than an aggregation one: separate workspaces are separate financial worlds (a personal life, a managed family member, someday a team), and nothing aggregates across workspaces by default — isolation there is a *feature*, purchased by the same hierarchy that makes aggregation inside a workspace cheap.

---

## 8. Portfolio Lifecycle

Lifecycle transitions change what a portfolio may do next; none of them ever edits what it already did. Every transition below is an *event layered onto a permanent identity* — the same rule the asset lifecycle follows (UNIVERSAL_ASSET_ARCHITECTURE.md §6), for the same reason: replay and evaluation are only trustworthy over histories that no transition can rewrite.

- **Create** — a `portfolio_id` is minted with its identity facts (§3), universe (§4), and policy (§5) declared up front. Declaring intent at birth is the point: a portfolio created "empty of rules, to be decided later" is a list, not a portfolio.
- **Activate** — the portfolio becomes transactable. Distinct from creation so that a portfolio can be fully configured, reviewed, even seeded by import, before its ledger opens for business.
- **Archive** — the portfolio leaves active management: no new transactions, but fully readable, replayable, and included in Wealth history. Archival is for strategies that ended; it preserves the story.
- **Clone** — a new `portfolio_id` born with a *copy of another's strategy, universe, and policy* — and none of its history. Clone answers "start another one like this"; it never shares a ledger, because two portfolios sharing history would be two names for one accounting boundary, which the model forbids.
- **Merge** — two strategies become one going forward. The domain rule: merge is a *forward-looking* event — positions transfer as explicit, mirrored ledger events into the surviving portfolio, and the source portfolio closes with its history intact and permanently attributable. History is never re-keyed, restated, or blended; each portfolio's past performance remains its own, exactly as recorded. (A merge that rewrote history would silently falsify every recommendation grade and attribution record either portfolio ever earned.)
- **Close** — the terminal state: the strategy's story is over, the boundary is sealed, and identity, ledger, snapshots, and evaluation history remain permanently addressable. Closed is not deleted. This platform never deletes financial history, because its evaluation machinery — and its owner's right to their own past — depends on finished stories staying readable.
- **Import** — a portfolio's beginning includes pre-existing reality: positions and history entering via the Universal Input Layer (PLATFORM_EVOLUTION.md §5) as properly classified ledger events — the discipline the platform already hardened for imported positions (non-performance inflows, truthfully stripped from returns) applies to portfolio-scale import identically.
- **Export** — the portfolio's truth leaves the platform: its ledger, its provenance, its computed history — complete enough to be audited or re-imported. Export is the honesty guarantee inverted: the platform holds nothing about a portfolio that its owner cannot take with them.

---

## 9. Portfolio Validation

Validation answers one question at the moment of intent: **is this action legitimate for this portfolio, right now?** It composes the platform's existing validation layers rather than replacing them — each layer answers only what it alone can know:

- **Asset allowed** — is the referenced `asset_id` real, resolved, and in a lifecycle state that permits transactions? (Answered by the Asset Registry — UNIVERSAL_ASSET_ARCHITECTURE.md §7. The portfolio never re-derives this.)
- **Market allowed** — does the asset's market fall within this portfolio's policy? A question only the portfolio can answer, because it is about *this* strategy's scope.
- **Currency allowed** — is the asset's native currency admissible under policy, and is the FX path to base currency canonical data rather than improvisation?
- **Universe allowed** — the headline check (§4): does this instrument belong in *this* portfolio's declared universe? The check that speaks the language of purpose.
- **Benchmark compatible** — a *warning-grade* check, not a gate: a portfolio whose holdings have drifted far from anything its benchmark represents hasn't done something invalid — but its performance numbers are becoming unmeaningful, and the platform's honesty duty is to say so.
- **Policy compatible** — the remaining rulebook (§5): cash floor after this action, fractional permission, leverage prohibition, settlement discipline, wrapper obligations.

### The validation philosophy

Four commitments, all inherited from the platform's constitution and applied at the portfolio level. **Validate at intent, not at damage** — the gate sits before the ledger event is recorded, because the ledger is immutable and prevention is the only cheap correction. **Layered, each layer sovereign** — the Registry validates what things *are*, the Market Data Platform validates *observations*, the portfolio validates *belonging and conduct*; no layer second-guesses another, no rule lives in two places (ADR-004, again). **Provider-independent and replay-stable** — every check reads the platform's own recorded state (Registry, policy, universe), never a live external answer, so validation's verdict is reproducible whenever the question is re-asked (the identical argument made in UNIVERSAL_ASSET_ARCHITECTURE.md §7). And **refusals explain themselves** — a rejected action states *which* declared rule it violated, in strategy language ("outside this portfolio's Thai Equity universe"), because a guardrail that can't explain itself trains users to fight it rather than trust it — the same explainability-as-fiduciary-duty the optimizer already owes for every trade it proposes.

---

## 10. Analytics Boundary

The hierarchy of §7 implies a division of analytical labor, and keeping it sharp prevents the most seductive category error in wealth platforms: benchmark-judging a net worth, or strategy-crediting a sum.

### Portfolio analytics — judgments about a strategy

Everything benchmark-relative, attribution-laden, or decision-evaluating lives at the portfolio level, because only there do "success" and "skill" have definitions:

- **Portfolio Return** — cash-flow-adjusted, boundary-clean, in base currency, by the frozen rules.
- **Portfolio Alpha** — return versus *this portfolio's* benchmark (§6); meaningless anywhere a benchmark isn't declared.
- **Portfolio Drawdown, volatility, risk metrics** — the strategy's risk story, judged against its own policy tolerances.
- **Attribution, recommendation grades, human-vs-AI, shadow comparisons** — the entire evaluation stack, which exists to judge *decisions made under a strategy* and therefore cannot outlive the strategy boundary.

### Wealth analytics — descriptions of a whole

Everything cross-cutting and benchmark-free lives at the Wealth level, computed by aggregation (§7), never recorded independently:

- **Total Net Worth** — the sum of portfolio NAVs in the reporting currency; a fact, not a performance claim.
- **Overall Allocation** — how the whole splits across asset classes, markets, currencies — regardless of which strategy holds what.
- **Overall Exposure** — identity-aware concentration across boundaries: the same asset, sector, or currency accumulated through three portfolios is one risk, and only the Wealth view can see it.
- **Overall Asset Mix, liquidity profile, goal coverage** — the questions of a financial *life*: how much is reachable in a week, how much is locked in wrappers, how the whole maps onto the person's goals.

### The rule at the boundary

**Portfolio analytics judge; Wealth analytics describe.** Alpha, grades, and attribution never aggregate upward — averaging the alpha of a retirement fund, a crypto experiment, and an emergency fund produces a number with units but no meaning. Net worth and exposure never disaggregate downward as judgments — a portfolio is not "doing badly" because it is a small share of the whole. Wealth-level *risk observation* (overall concentration) may legitimately inform portfolio-level *policy* — but through the front door: as input to a policy the owner declares (§5), never as a hidden cross-boundary constraint an engine invents. The boundary is crossed by people making decisions, not by analytics leaking sideways.

---

## 11. Future Expansion

The test, as always: each future capability must be an act of *description* — a universe, a policy, a benchmark choice, a goal profile — never surgery on the Portfolio Engine. Walking the roadmap's Phase 5 ambitions through the model:

- **Retirement** — a portfolio with a Retirement universe (tax-advantaged wrappers in scope), a policy carrying RMF/SSF holding obligations, a policy or category benchmark, and a goal profile with a target date. Every piece already has a home; the engine replays its ledger like any other.
- **Goal-based investing generally** — the goal-profile concept the platform already shipped, generalized: a goal is *strategy metadata that shapes recommendations and defines success*, not an accounting concept. Goal-aware advice reads the goal; the ledger never knows it exists.
- **Education Fund / Wedding Fund** — date-bound goals with conservative universes and glide-path-shaped policy (risk tolerance that tightens as the date nears — a *policy schedule*, which is still just policy). The date changes what advice looks like, never what accounting looks like.
- **Emergency Fund** — the degenerate case that proves the model: universe of cash and near-cash, policy of high liquidity and no risk, **No Benchmark** (§6), goal defined as a floor amount rather than growth. A portfolio that is deliberately not investing is still perfectly a portfolio — strategy, policy, boundary, all present.
- **Property** — a portfolio (or a holding within a Multi-Asset one) whose assets are appraisal-priced with honest staleness (MARKET_DATA_PLATFORM.md §11), whose income is RENT-type ledger events, whose universe admits illiquid assets. Everything unusual about property was already absorbed two documents ago, at the asset and data layers; by the time property reaches the portfolio, it is just holdings and ledger events.
- **Alternative assets** — private equity, collectibles, whatever arrives: the asset layer describes them (UNIVERSAL_ASSET_ARCHITECTURE.md §11), the data layer prices them honestly, and the portfolio layer needs only a universe willing to contain them. Three layers of description; zero layers of engine change.

The pattern across all six: the Portfolio Engine replays ledgers inside boundaries, and *nothing on this list changes what a ledger or a boundary is*. Strategy variety lands entirely in the declarative surface — universe, policy, benchmark, goal — which is exactly the surface this document exists to define.

---

## 12. Principles

1. **A Portfolio is a strategy, a policy, and an accounting boundary — always all three.** An object missing any leg is a list, and the platform does not manage lists.
2. **The Portfolio is an accounting boundary; the boundary is sacred.** One ledger per portfolio, every event in exactly one ledger, all state derived by replay, nothing crossing the boundary unclassified.
3. **Investment Universe drives validation.** Belonging is a fact about the strategy, not the instrument. "Not *here*" is the platform's most useful refusal, and only the universe can say it.
4. **Policy is one declared rulebook, read by everything, owned by nothing else.** Validation, optimization, and execution consume the same policy; no engine grows a private copy of a portfolio's rules.
5. **Benchmark belongs to the Portfolio, because success is defined per strategy.** Composite, policy-derived, categorical, or explicitly none — and every evaluation number downstream is only as honest as this choice.
6. **Wealth aggregates Portfolios; it never becomes one.** No ledger at the Wealth level, no benchmark on a net worth, no judgment without a strategy to judge.
7. **Portfolio analytics judge; Wealth analytics describe.** Alpha never averages upward; net worth never scolds downward.
8. **Business logic never depends on Asset Type alone.** Universes, policies, and capabilities carry the meaning that raw type checks fake — at the portfolio layer exactly as at the engine layer.
9. **Lifecycle changes the future, never the past.** Create, archive, merge, close — every transition is an event on a permanent identity, and no transition re-keys, restates, or deletes recorded history.
10. **Strategy variety is declarative; the engine is invariant.** Every future kind of portfolio — retirement, goal, property, unknown — arrives as a new declaration over the same deterministic replay, or the model has failed and the *model* gets fixed.

---

## Related Documents

- [PLATFORM_EVOLUTION.md](PLATFORM_EVOLUTION.md) — the platform philosophy and invariants this model operates under
- [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md) — the Asset and Registry model that portfolios compose
- [MARKET_DATA_PLATFORM.md](MARKET_DATA_PLATFORM.md) — the canonical observations portfolios are valued against
- [../investment/PORTFOLIO_CALCULATION_RULES.md](../investment/PORTFOLIO_CALCULATION_RULES.md) — the frozen accounting semantics inside the boundary
- [../investment/OPTIMIZER_PHILOSOPHY.md](../investment/OPTIMIZER_PHILOSOPHY.md) — the decision-layer constitution that consumes portfolio strategy, policy, and universe
- [../engineering/DECISION_LOG.md](../engineering/DECISION_LOG.md) — the recorded boundary-defense decisions (import stripping, cash-flow adjustment, correction handling) this model generalizes
