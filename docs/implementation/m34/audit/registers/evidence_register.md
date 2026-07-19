# M34 Evidence Register

**Status:** Active. Contains M34-WP2 product evidence, M34-WP3 route-level
inventory evidence, M34-WP4 static read-contract and observable-lineage
evidence, and M34-WP5 semantic-authority evidence.

**Governing protocol:**
`../../../M34_WP1_charter_and_audit_protocol.md`

**Working-artifact rules:** `../README.md`

## Use

This register is the canonical metadata record for M34 evidence. M34-WP2
contains bounded product-structure, documentation, and repository-search
observations. M34-WP3 adds static route inventory and derived classifications.
M34-WP4 adds client, route, service, read-model, persistence-source, and
transformation lineage without judging semantics. M34-WP5 adds the governing
semantic-authority corpus, claim-family coverage, ownership conflicts, and
the bounded authority-readiness result. Later work packages allocate
new ids rather than rewriting these records.

Allowed classes are `DIRECT`, `DERIVED`, `RUNTIME`, `DOCUMENTATION`, `TEST`,
`UNKNOWN`, and `ASSUMPTION`. Allowed statuses are `DRAFT`, `CAPTURED`,
`VERIFIED`, `DISPUTED`, and `SUPERSEDED`.

Only `VERIFIED` evidence that is not superseded may support an approved
disposition or readiness decision.

## Record template

Copy the block below when allocating the next evidence id. Replace every
placeholder; never leave a required field blank.

```markdown
## M34-E-NNNN - <short factual title>

- Status: DRAFT
- Class: <DIRECT | DERIVED | RUNTIME | DOCUMENTATION | TEST | UNKNOWN | ASSUMPTION>
- Work package: <M34-WP#>
- Captured at UTC: <YYYY-MM-DDTHH:MM:SSZ>
- Captured by: <reviewer identity or approved role>
- Verified by: PENDING
- Verified at UTC: PENDING
- Repository revision: <full commit hash | explicit dirty-worktree boundary | NONE>
- Environment: <environment identity | STATIC_REPOSITORY | NONE>
- Corpus ids: <M34-C-NNNN[, ...]>
- Premise evidence ids: <sorted ids | NONE>
- Linked finding ids: <sorted ids | NONE>
- Supersedes: <M34-E-NNNN | NONE>
- Superseded by: <M34-E-NNNN | NONE>

### Source locator

- Path or environment locator: <stable repository-relative or runtime locator>
- Symbol, route, section, schema, command, or fixture: <stable locator | NONE>
- Supporting artifact: <relative path | NONE>

### Factual observation

<Minimal statement of what was directly observed. No interpretation or
disposition.>

### Capture method

<Read-only command, inspection method, query boundary, or execution method.>

### Derived method

<Reproducible transformation/reasoning and premise ids for DERIVED evidence;
otherwise NONE.>

### Normative authority

- Authority level: <constitutional | domain | ADR/decision | specification | descriptive | NONE>
- Governing reference: <stable locator | NONE>

### Limitations, conflicts, and search bounds

<Environment limits, unavailable facts, contradictions, negative-search
scope, or NONE.>

### Redaction and sensitivity

<Sanitization performed, prohibited material excluded, or NONE.>

### Verification record

- Review ids: <sorted M34-R-NNNN ids | PENDING>
- Verification result: <PENDING | reproduced factual observation | dispute summary>
```

## Records

## M34-E-0001 - Authentication lands on the legacy root dashboard

- Status: `VERIFIED`
- Class: `DIRECT`
- WP2 claim class: `OBSERVED`
- Work package: `M34-WP2`
- Captured at UTC: 2026-07-17T11:33:15Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-17T11:33:15Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0004`, `M34-C-0017`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `frontend/app/login/page.tsx::handleSubmit`; `frontend/components/AppShell.tsx::AppShell`
- Symbol, route, section, schema, command, or fixture: `router.replace("/")`; authenticated shell render
- Supporting artifact: `NONE`

### Factual observation

Successful login replaces the route with `/`. Every non-login route is then
rendered inside `PortfolioProvider` with the global `Navbar`.

### Capture method

Read-only source inspection plus `rg` for post-login router calls.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

Static route behavior only; no browser session was executed.

### Redaction and sensitivity

No credential values inspected.

### Verification record

- Review ids: `M34-R-0001`
- Verification result: Source composition and route replacement reproduced by separate targeted reads.

## M34-E-0002 - Global navigation groups portfolio and AI destinations

- Status: `VERIFIED`
- Class: `DIRECT`
- WP2 claim class: `OBSERVED`
- Work package: `M34-WP2`
- Captured at UTC: 2026-07-17T11:33:15Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-17T11:33:15Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0005`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `frontend/components/Navbar.tsx::NAV_MAIN`; `frontend/components/Navbar.tsx::Navbar`
- Symbol, route, section, schema, command, or fixture: global brand, main links, route matches, portfolio selector
- Supporting artifact: `NONE`

### Factual observation

The brand links to `/`. The main Portfolio item links to `/portfolio` and is
active for `/portfolio`, `/performance`, `/analytics`, and `/stock`. The AI
Operations item links to `/operations-center` and is active for
`/portfolio-intelligence`. The same navigation data is rendered on desktop and
mobile. The navbar also exposes the shared active-portfolio selector.

### Capture method

Read-only UTF-8 source inspection of navigation arrays and both render paths.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

Observed code structure; actual click frequency and discoverability are
unknown.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0001`
- Verification result: Destinations and match prefixes reproduced from exact arrays.

## M34-E-0003 - One active portfolio context is shared across routes

- Status: `VERIFIED`
- Class: `DIRECT`
- WP2 claim class: `OBSERVED`
- Work package: `M34-WP2`
- Captured at UTC: 2026-07-17T11:33:15Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-17T11:33:15Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0006`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `frontend/lib/PortfolioContext.tsx::PortfolioProvider`
- Symbol, route, section, schema, command, or fixture: `activeId`, `setActiveId`, `active_portfolio_id`
- Supporting artifact: `NONE`

### Factual observation

The provider loads portfolios, restores a valid selected id from local storage
or selects the first portfolio, and exposes one `activeId` and setter to its
consumers.

### Capture method

Read-only source inspection.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

No browser execution and no judgment of persistence or error semantics.

### Redaction and sensitivity

No local-storage values inspected.

### Verification record

- Review ids: `M34-R-0001`
- Verification result: State initialization and setter behavior reproduced from the source.

## M34-E-0004 - Portfolio secondary navigation has three destinations

- Status: `VERIFIED`
- Class: `DIRECT`
- WP2 claim class: `OBSERVED`
- Work package: `M34-WP2`
- Captured at UTC: 2026-07-17T11:33:15Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-17T11:33:15Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0007`, `M34-C-0009`, `M34-C-0010`, `M34-C-0011`, `M34-C-0012`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `frontend/components/PortfolioTabs.tsx::TABS`
- Symbol, route, section, schema, command, or fixture: `/portfolio`, `/performance`, `/analytics`
- Supporting artifact: `NONE`

### Factual observation

The component labels and links Overview, Returns, and Deep Analytics as one
Portfolio secondary-navigation set. The overview, performance, analytics, and
factor pages render this component.

### Capture method

Read-only source inspection plus a bounded `rg -l` search for
`PortfolioTabs` imports/renders in `frontend/app/**/page.tsx`.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

Presence does not prove that users perceive the routes as one coherent area.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0001`
- Verification result: Destinations and four page usages reproduced.

## M34-E-0005 - Root dashboard aggregates portfolios into a stock heatmap

- Status: `VERIFIED`
- Class: `DIRECT`
- WP2 claim class: `OBSERVED`
- Work package: `M34-WP2`
- Captured at UTC: 2026-07-17T11:33:15Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-17T11:33:15Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0008`, `M34-C-0015`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `frontend/app/page.tsx::DashboardPage`; `frontend/app/page.tsx::PortfolioHeatmap`
- Symbol, route, section, schema, command, or fixture: `/`; `/stock/[symbol]`
- Supporting artifact: `NONE`

### Factual observation

The root Dashboard loads holdings and prices for every portfolio from the
shared portfolio list, aggregates holdings by symbol into a Portfolio Heatmap,
and links each tile to stock detail.

### Capture method

Read-only source inspection.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

No valuation, aggregation, or freshness semantics were evaluated.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0002`
- Verification result: Multi-portfolio load loop, aggregation, and outbound links reproduced.

## M34-E-0006 - Portfolio overview combines maintenance, holdings, and investigation tasks

- Status: `VERIFIED`
- Class: `DIRECT`
- WP2 claim class: `OBSERVED`
- Work package: `M34-WP2`
- Captured at UTC: 2026-07-17T11:33:15Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-17T11:33:15Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0009`, `M34-C-0014`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `frontend/app/portfolio/page.tsx::PortfolioPage`; `frontend/components/PortfolioTable.tsx`
- Symbol, route, section, schema, command, or fixture: `/portfolio`
- Supporting artifact: `NONE`

### Factual observation

The route exposes portfolio selection/creation/deletion; buy, sell, deposit,
withdraw, dividend, and existing-position import actions; price refresh and
analysis actions; cash, holdings, portfolio allocation, sector allocation;
links to Portfolio DNA and stock detail.

### Capture method

Read-only inspection of user-facing controls, sections, and links.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

Exposed capability does not establish usage, value, correctness, or task
success.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0002`
- Verification result: Labels and route links reproduced from the render tree.

## M34-E-0007 - Performance route exposes snapshot and return-investigation tasks

- Status: `VERIFIED`
- Class: `DIRECT`
- WP2 claim class: `OBSERVED`
- Work package: `M34-WP2`
- Captured at UTC: 2026-07-17T11:33:15Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-17T11:33:15Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0010`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `frontend/app/performance/page.tsx::PerformancePage`
- Symbol, route, section, schema, command, or fixture: `/performance`; `/ai-analytics/attribution`
- Supporting artifact: `NONE`

### Factual observation

The route exposes snapshot generation/history, value and P/L summaries,
investment-return breakdowns, an equity curve, benchmark comparison, latest
holdings, and an explicit “Why this return? See Attribution” link to the AI
Evaluation attribution route.

### Capture method

Read-only inspection of user-facing controls, sections, and links.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

No calculation or explanation-quality assessment.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0002`
- Verification result: Sections and cross-hub link reproduced.

## M34-E-0008 - Analytics route exposes quantitative investigation tasks

- Status: `VERIFIED`
- Class: `DIRECT`
- WP2 claim class: `OBSERVED`
- Work package: `M34-WP2`
- Captured at UTC: 2026-07-17T11:33:15Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-17T11:33:15Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0011`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `frontend/app/analytics/page.tsx::AnalyticsPage`
- Symbol, route, section, schema, command, or fixture: `/analytics`
- Supporting artifact: `NONE`

### Factual observation

The route exposes portfolio performance KPIs, monthly returns, benchmark
comparison, drawdown/equity charts, signal analytics, allocation analytics,
benchmark selection, and time-range selection for the active portfolio.

### Capture method

Read-only inspection of user-facing sections and controls.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

No analytics semantic or correctness assessment.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0002`
- Verification result: Sections and controls reproduced.

## M34-E-0009 - Portfolio routes provide factor and stock drill-down paths

- Status: `VERIFIED`
- Class: `DIRECT`
- WP2 claim class: `OBSERVED`
- Work package: `M34-WP2`
- Captured at UTC: 2026-07-17T11:33:15Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-17T11:33:15Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0012`, `M34-C-0014`, `M34-C-0015`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `frontend/app/portfolio/[id]/factors/page.tsx`; `frontend/components/PortfolioTable.tsx`; `frontend/app/stock/[symbol]/page.tsx`
- Symbol, route, section, schema, command, or fixture: `/portfolio/[id]/factors`; `/stock/[symbol]`
- Supporting artifact: `NONE`

### Factual observation

Portfolio overview links to a portfolio-id-specific DNA Analysis route. That
route renders Portfolio tabs and a breadcrumb back to `/portfolio`. Holdings
symbols link to stock detail; stock detail supplies back navigation and
analysis sections.

### Capture method

Read-only inspection plus bounded link search.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

No browser history or task-completion observation.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0002`
- Verification result: Inbound links and return controls reproduced.

## M34-E-0010 - Portfolio Intelligence is reached through the AI Operations context

- Status: `VERIFIED`
- Class: `DIRECT`
- WP2 claim class: `OBSERVED`
- Work package: `M34-WP2`
- Captured at UTC: 2026-07-17T11:33:15Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-17T11:33:15Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0013`, `M34-C-0016`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `frontend/components/operations-center/OperationsCenter.tsx`; `frontend/app/portfolio-intelligence/page.tsx`
- Symbol, route, section, schema, command, or fixture: `/operations-center`; `/portfolio-intelligence`
- Supporting artifact: `NONE`

### Factual observation

Operations Center explicitly links to Portfolio Intelligence. The destination
uses the shared active portfolio, breadcrumbs back to Operations Center,
describes itself as a Decision Memory System, and exposes Human-vs-AI, regret,
calibration, regime, shadow-portfolio, and decision-timeline panels. It does
not render Portfolio tabs.

### Capture method

Read-only inspection of link, header, breadcrumb, and panel composition.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

No claim that this separation is good, bad, or confusing.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0002`
- Verification result: Parent link, return link, active context, and sections reproduced.

## M34-E-0011 - System Guide documents one Portfolio center with three tabs

- Status: `VERIFIED`
- Class: `DOCUMENTATION`
- WP2 claim class: `DOCUMENTED`
- Work package: `M34-WP2`
- Captured at UTC: 2026-07-17T11:33:15Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-17T11:33:15Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0018`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `frontend/app/system-guide/page.tsx::NavigationOverview`
- Symbol, route, section, schema, command, or fixture: navigation cards and stock-analysis journey
- Supporting artifact: `NONE`

### Factual observation

The in-product guide describes Portfolio as the center for everything about a
portfolio, divided into Overview, Returns, and Deep Analytics tabs. It assigns
holdings/transactions/DNA to Overview, NAV/snapshots/benchmarks to Returns,
and quantitative KPIs/heatmap/drawdown/Sharpe to Deep Analytics. It separately
documents Portfolio Intelligence as decision memory reached from the AI
Operations Center.

### Capture method

Read-only documentation inspection.

### Derived method

`NONE`

### Normative authority

- Authority level: `descriptive`
- Governing reference: `frontend/app/system-guide/page.tsx`

### Limitations, conflicts, and search bounds

Describes intended use; does not prove user understanding or behavior.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0003`
- Verification result: Descriptions reproduced from the guide's navigation section.

## M34-E-0012 - Roadmap claims broad portfolio and analytical capability

- Status: `VERIFIED`
- Class: `DOCUMENTATION`
- WP2 claim class: `DOCUMENTED`
- Work package: `M34-WP2`
- Captured at UTC: 2026-07-17T11:33:15Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-17T11:33:15Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0019`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/architecture/ROADMAP.md`
- Symbol, route, section, schema, command, or fixture: Portfolio Engine, Performance Analytics, Execution Intelligence, AI Evaluation, Portfolio Intelligence
- Supporting artifact: `NONE`

### Factual observation

The roadmap marks transactions, replay, snapshots, metrics, benchmark,
performance history, accounting, major performance analytics, execution
intelligence, and AI Evaluation as completed, while listing additional rolling,
risk, position-attribution, and sector-attribution work under Portfolio
Intelligence.

### Capture method

Read-only documentation inspection.

### Derived method

`NONE`

### Normative authority

- Authority level: `specification`
- Governing reference: `docs/architecture/ROADMAP.md`

### Limitations, conflicts, and search bounds

Capability status does not prove correctness, adoption, frequency, or user
value.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0003`
- Verification result: Relevant completed and future capability lists reproduced.

## M34-E-0013 - Domain documentation separates portfolio scope from whole-picture scope

- Status: `VERIFIED`
- Class: `DOCUMENTATION`
- WP2 claim class: `DOCUMENTED`
- Work package: `M34-WP2`
- Captured at UTC: 2026-07-17T11:33:15Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-17T11:33:15Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0020`, `M34-C-0021`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/architecture/PORTFOLIO_DOMAIN_MODEL.md`; `docs/GLOSSARY.md::Platform Domains`
- Symbol, route, section, schema, command, or fixture: responsibilities and Wealth hierarchy
- Supporting artifact: `NONE`

### Factual observation

The Portfolio domain model documents a portfolio as one strategy, policy, and
accounting boundary owning portfolio-scoped holdings, transactions,
accounting, performance, benchmark, risk, analytics, and evaluation scope. It
documents whole-financial-picture ownership/allocation questions as Wealth
aggregation. The glossary defines Portfolio Intelligence as what truth means
and Experience Platform as how a person meets it.

### Capture method

Read-only documentation inspection.

### Derived method

`NONE`

### Normative authority

- Authority level: `domain`
- Governing reference: `docs/architecture/PORTFOLIO_DOMAIN_MODEL.md`; `docs/GLOSSARY.md`

### Limitations, conflicts, and search bounds

No implementation-conformance assessment and no reinterpretation of the
approved M34 user questions.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0003`
- Verification result: Domain responsibility and hierarchy statements reproduced.

## M34-E-0014 - Navigation and shared-context counts

- Status: `VERIFIED`
- Class: `DERIVED`
- WP2 claim class: `MEASURED`
- Work package: `M34-WP2`
- Captured at UTC: 2026-07-17T11:33:15Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-17T11:33:15Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0001`, `M34-C-0005`, `M34-C-0006`, `M34-C-0007`
- Premise evidence ids: `M34-E-0001`, `M34-E-0002`, `M34-E-0003`, `M34-E-0004`, `M34-E-0005`, `M34-E-0006`, `M34-E-0007`, `M34-E-0008`, `M34-E-0009`, `M34-E-0010`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `command::WP2 route/navigation inventory`
- Symbol, route, section, schema, command, or fixture: `rg --files`, `rg -l`, explicit array counts
- Supporting artifact: `NONE`

### Factual observation

The current `NAV_MAIN` array has five entries. `PortfolioTabs` has three
destinations and is rendered by four page files. Eighteen page files call
`usePortfolio()`. The inspected explicit links and redirects form nine
portfolio-relevant destinations in the WP2 navigation map: `/`, `/portfolio`,
`/performance`, `/analytics`, `/portfolio/[id]/factors`, `/stock/[symbol]`,
`/operations-center`, `/portfolio-intelligence`, and
`/ai-analytics/attribution`.

### Capture method

Counted exact arrays and bounded `frontend/app/**/page.tsx` search results;
route map retained only destinations supported by `M34-E-0001` through
`M34-E-0010`.

### Derived method

Lexical file enumeration and exact-match counts over the cited source arrays
and use sites. No route weighting or product interpretation.

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

Counts describe repository topology, not user traffic, task frequency,
discoverability, or fragmentation harm.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0001`
- Verification result: Counts reproduced with independent file and content searches.

## M34-E-0015 - No product-behavior instrumentation found in the frontend boundary

- Status: `VERIFIED`
- Class: `DIRECT`
- WP2 claim class: `MEASURED`
- Work package: `M34-WP2`
- Captured at UTC: 2026-07-17T11:33:15Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-17T11:33:15Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0001`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `command::bounded product-analytics search`
- Symbol, route, section, schema, command, or fixture: `frontend/`; `frontend/package.json`
- Supporting artifact: `NONE`

### Factual observation

A case-insensitive bounded search returned zero matches for PostHog, Mixpanel,
Segment tracking, `analytics.track`, `gtag`, Google Analytics,
`useReportWebVitals`, Plausible, Amplitude, Heap tracking, Hotjar, or FullStory.

### Capture method

`rg` over `frontend/` and `frontend/package.json` using the explicit product-
analytics pattern list above.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

Does not prove that external hosting, proxy, or undocumented systems collect
usage data. It proves only zero matches in the named repository boundary and
pattern set.

### Redaction and sensitivity

No environment values or telemetry payloads inspected.

### Verification record

- Review ids: `M34-R-0004`
- Verification result: Bounded search reproduced with zero matches.

## M34-E-0016 - No user-research or task-performance artifact found in documentation

- Status: `VERIFIED`
- Class: `DIRECT`
- WP2 claim class: `MEASURED`
- Work package: `M34-WP2`
- Captured at UTC: 2026-07-17T11:33:15Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-17T11:33:15Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0002`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `command::bounded user-evidence search`
- Symbol, route, section, schema, command, or fixture: `docs/**/*.md`
- Supporting artifact: `NONE`

### Factual observation

A case-insensitive bounded search returned zero matches for user research,
usability tests, customer/user interviews, session replay, clickstream, task
completion, time on task, navigation failure, user/customer feedback, or
product analytics.

### Capture method

`rg` over repository Markdown beneath `docs/` using the explicit evidence-term
list above.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

Does not prove no external interviews, support conversations, usage reports,
or unpublished research exist. It proves only zero matches in the named
repository boundary and pattern set.

### Redaction and sensitivity

No personal data or external systems inspected.

### Verification record

- Review ids: `M34-R-0004`
- Verification result: Bounded search reproduced with zero matches.

## M34-E-0017 - Complete frontend route-page accounting

- Status: `VERIFIED`
- Class: `DIRECT`
- Work package: `M34-WP3`
- Captured at UTC: 2026-07-19T07:33:12Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T07:33:12Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0022`, `M34-C-0039`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `frontend/app/**/page.tsx`
- Symbol, route, section, schema, command, or fixture: complete route-page file list
- Supporting artifact: `../reports/M34_WP3_surface_and_user_question_inventory.md`

### Factual observation

The audited revision contains 24 route-page files. Twenty-two present or
affect portfolio-facing claims, context, investigation, configuration, or
explanation. `/login` establishes entry only, and `/ai-analytics/system`
presents system telemetry without portfolio context.

### Capture method

`rg --files frontend/app` filtered to `page.tsx`, followed by read-only
inspection of imports, headings, route context, and primary dependencies for
every returned file.

### Derived method

`NONE`

### Normative authority

- Authority level: `specification`
- Governing reference: `docs/implementation/M34_WP1_charter_and_audit_protocol.md::1.2 Scope`

### Limitations, conflicts, and search bounds

Static repository route pages only. Runtime-only, external, or feature-flagged
surfaces outside this file universe remain unknown.

### Redaction and sensitivity

No runtime data, secrets, or personal data inspected.

### Verification record

- Review ids: `M34-R-0005`
- Verification result: Route listing and 24 = 22 included + 2 excluded accounting reproduced.

## M34-E-0018 - Shared navigation establishes current route parents

- Status: `VERIFIED`
- Class: `DIRECT`
- Work package: `M34-WP3`
- Captured at UTC: 2026-07-19T07:33:12Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T07:33:12Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0024`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `frontend/components/Navbar.tsx`; `frontend/components/PortfolioTabs.tsx`; `frontend/app/ai-analytics/(hub)/layout.tsx`; `frontend/components/evaluation/EvaluationTabs.tsx`
- Symbol, route, section, schema, command, or fixture: `NAV_MAIN`; `TABS`; `EvaluationHubLayout`
- Supporting artifact: `../reports/M34_WP3_surface_and_user_question_inventory.md::6. Navigation Ownership Map`

### Factual observation

The global navbar parents Portfolio, Watchlist, AI Operations, AI Evaluation,
and Guide routes. Portfolio has three tab destinations. The AI Evaluation
route group has six tab destinations, while record detail and opportunity-cost
routes inherit or link back to their list/parent routes.

### Capture method

Read-only inspection of navigation arrays, route-group layout, active matching,
and explicit links/breadcrumbs in included routes.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

Static route relationships only; discoverability, user comprehension, and
runtime navigation behavior were not measured.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0006`, `M34-R-0007`
- Verification result: Navigation destinations and parent/detail relationships reproduced from exact source arrays and links.

## M34-E-0019 - AI Operations routes expose portfolio-scoped status and actions

- Status: `VERIFIED`
- Class: `DIRECT`
- Work package: `M34-WP3`
- Captured at UTC: 2026-07-19T07:33:12Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T07:33:12Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0034`, `M34-C-0035`, `M34-C-0036`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `frontend/app/operations-center/page.tsx`; `frontend/components/operations-center/OperationsCenter.tsx`; `frontend/app/optimizer/page.tsx`; `frontend/app/goal-wizard/page.tsx`; `frontend/components/goal/GoalWizard.tsx`
- Symbol, route, section, schema, command, or fixture: route components, major headings, imports, and visible actions
- Supporting artifact: `../reports/M34_WP3_surface_and_user_question_inventory.md::2.2 AI Operations and portfolio-intelligence surfaces`

### Factual observation

All three routes require the active portfolio. Operations Center presents
portfolio/AI status and can run the optimizer. Optimizer presents analysis,
recommendation, history, policy/persona, and existing decision controls. Goal
Wizard captures and persists a goal profile and states that it provides no
projection, forecast, or advice.

### Capture method

Read-only inspection of route context, host components, imports, headings,
links, and user actions. Calculation bodies were not inspected.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

This observes exposed claims and commands only. It does not validate optimizer,
goal, policy, recommendation, or decision semantics and does not reopen M32 or
M33.

### Redaction and sensitivity

No runtime data or credentials inspected.

### Verification record

- Review ids: `M34-R-0007`
- Verification result: Active-portfolio dependencies, major output sections, and action/import boundaries reproduced.

## M34-E-0020 - Nine portfolio-scoped AI Evaluation routes are present

- Status: `VERIFIED`
- Class: `DIRECT`
- Work package: `M34-WP3`
- Captured at UTC: 2026-07-19T07:33:12Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T07:33:12Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0024`, `M34-C-0025`, `M34-C-0026`, `M34-C-0027`, `M34-C-0028`, `M34-C-0029`, `M34-C-0030`, `M34-C-0031`, `M34-C-0032`, `M34-C-0033`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `frontend/app/ai-analytics/(hub)/**/page.tsx`; `frontend/app/ai-analytics/(hub)/layout.tsx`
- Symbol, route, section, schema, command, or fixture: nine route components and shared layout
- Supporting artifact: `../reports/M34_WP3_surface_and_user_question_inventory.md::2.3 AI Evaluation surfaces`

### Factual observation

The route group contains scorecard, recommendations list/detail, execution
list/detail, human-versus-AI, opportunity cost, portfolio comparison, and
attribution surfaces. Each reads the active portfolio; the two detail routes
also use a route record id. The inspected pages expose only read client calls.

### Capture method

Complete route-file enumeration plus read-only inspection of purpose comments,
headings, links, `usePortfolio`, route parameters, and imported API calls.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

Page comments claiming verbatim rendering were observed but not verified.
Metrics, counterfactuals, attribution, grading, and execution terminology were
not judged.

### Redaction and sensitivity

No runtime evaluation records inspected.

### Verification record

- Review ids: `M34-R-0007`
- Verification result: Nine-route count, active-portfolio use, record ids, headings, and imported client functions reproduced.

## M34-E-0021 - Adjacent routes expose watchlist and settings claims

- Status: `VERIFIED`
- Class: `DIRECT`
- Work package: `M34-WP3`
- Captured at UTC: 2026-07-19T07:33:12Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T07:33:12Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0037`, `M34-C-0038`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `frontend/app/watchlist/page.tsx`; `frontend/app/settings/page.tsx`
- Symbol, route, section, schema, command, or fixture: route components and portfolio-relevant sections
- Supporting artifact: `../reports/M34_WP3_surface_and_user_question_inventory.md::2.4 Adjacent, administrative, and explanatory surfaces`

### Factual observation

Watchlist presents instrument-monitoring claims and uses the active portfolio
only for its buy action. Settings exposes system-wide portfolio and sector
limits plus data management.

### Capture method

Read-only inspection of route headings, portfolio context, links, imported API
functions, and portfolio-relevant settings sections.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

No setting, watchlist fact, transaction, or analysis output was validated.

### Redaction and sensitivity

No environment settings or user data inspected.

### Verification record

- Review ids: `M34-R-0006`
- Verification result: Mixed watchlist scope and portfolio-relevant settings sections reproduced from source.

## M34-E-0022 - Included surfaces link to explicit frontend API contracts

- Status: `VERIFIED`
- Class: `DIRECT`
- Work package: `M34-WP3`
- Captured at UTC: 2026-07-19T07:33:12Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T07:33:12Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0023`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `frontend/lib/api.ts`
- Symbol, route, section, schema, command, or fixture: functions imported by the 22 WP3 surfaces and directly rendered host components
- Supporting artifact: `../reports/M34_WP3_surface_and_user_question_inventory.md::2. Surface inventory`

### Factual observation

Each dynamic included surface can be linked to named client functions whose
current HTTP path and method are explicit in `frontend/lib/api.ts`. Static
System Guide is the only included surface without a data API. The methods
support the WP3 `READ`, `WRITE`, and `MIXED` inventory classifications.

### Capture method

For each included route, extract named imports and direct host-component calls,
then locate the corresponding exported client function and its method/path.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

Frontend transport declarations are linked contracts, not proof of backend
side effects, idempotency, semantic correctness, source authority, or runtime
availability.

### Redaction and sensitivity

No request payload values, tokens, or environment URLs inspected.

### Verification record

- Review ids: `M34-R-0006`, `M34-R-0007`
- Verification result: Named imports and exported method/path declarations reproduced for every dynamic included surface.

## M34-E-0023 - Surface-to-user-question classification

- Status: `VERIFIED`
- Class: `DERIVED`
- Work package: `M34-WP3`
- Captured at UTC: 2026-07-19T07:33:12Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T07:33:12Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0022`
- Premise evidence ids: `M34-E-0005`, `M34-E-0006`, `M34-E-0007`, `M34-E-0008`, `M34-E-0009`, `M34-E-0010`, `M34-E-0011`, `M34-E-0019`, `M34-E-0020`, `M34-E-0021`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/implementation/m34/audit/reports/M34_WP3_surface_and_user_question_inventory.md`
- Symbol, route, section, schema, command, or fixture: `3. User Question Matrix`
- Supporting artifact: `../reports/M34_WP3_surface_and_user_question_inventory.md`

### Factual observation

Every included surface is mapped to zero or more of the five canonical M34
questions as a primary or secondary visible claim.

### Capture method

For each route, compare explicit headings, labels, actions, and purpose comments
with the exact five WP1 questions; use `-` when no supported mapping exists.

### Derived method

Deterministic classification from the listed direct/documentation premise
evidence. No user priority, correctness, or completeness inference is added.

### Normative authority

- Authority level: `specification`
- Governing reference: `docs/implementation/M34_WP1_charter_and_audit_protocol.md::1.2 Scope`

### Limitations, conflicts, and search bounds

Maps what the repository claims to answer, not what users need or whether the
answer is true.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0008`
- Verification result: Every one of the 22 included surfaces has one matrix row and a premise-supported mapping.

## M34-E-0024 - Surface read-write and portfolio-scope classification

- Status: `VERIFIED`
- Class: `DERIVED`
- Work package: `M34-WP3`
- Captured at UTC: 2026-07-19T07:33:12Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T07:33:12Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0022`
- Premise evidence ids: `M34-E-0003`, `M34-E-0017`, `M34-E-0019`, `M34-E-0020`, `M34-E-0021`, `M34-E-0022`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/implementation/m34/audit/reports/M34_WP3_surface_and_user_question_inventory.md`
- Symbol, route, section, schema, command, or fixture: `4. Read vs Write Matrix`; `5. Portfolio Scope Matrix`
- Supporting artifact: `../reports/M34_WP3_surface_and_user_question_inventory.md`

### Factual observation

All 22 included surfaces have one route-level read/write class and one scope
class derived from their frontend API methods, active-portfolio dependency,
route parameters, or static content.

### Capture method

Classify a surface `MIXED` when any inspected route/host action declares a
POST, PUT, PATCH, or DELETE; otherwise `READ`, except Goal Wizard's write-only
route. Determine scope from collection iteration, active id, route id, symbol,
record id, or absence of portfolio context.

### Derived method

Apply the stated rules uniformly to `M34-E-0017` and the direct route/API
premises.

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

HTTP GET is classified as a route read without asserting backend idempotency.
Authorization, tenancy, persistence, and side-effect correctness are excluded.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0008`
- Verification result: Each included surface appears exactly once in both matrices and matches its inspected route/client dependencies.

## M34-E-0025 - Navigation ownership projection

- Status: `VERIFIED`
- Class: `DERIVED`
- Work package: `M34-WP3`
- Captured at UTC: 2026-07-19T07:33:12Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T07:33:12Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0022`
- Premise evidence ids: `M34-E-0002`, `M34-E-0004`, `M34-E-0007`, `M34-E-0009`, `M34-E-0010`, `M34-E-0018`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/implementation/m34/audit/reports/M34_WP3_surface_and_user_question_inventory.md`
- Symbol, route, section, schema, command, or fixture: `6. Navigation Ownership Map`
- Supporting artifact: `../reports/M34_WP3_surface_and_user_question_inventory.md`

### Factual observation

The map projects every included route into its current static global, tab,
drill-down, breadcrumb, or admin parent relationship.

### Capture method

Normalize exact source links and active-route arrays into one tree without
moving, renaming, or reprioritizing a route.

### Derived method

Union of all explicit route relationships in the premise evidence; Experience
is assigned only navigation ownership.

### Normative authority

- Authority level: `constitutional`
- Governing reference: `docs/implementation/M34_WP1_charter_and_audit_protocol.md::1.5 Ownership model`

### Limitations, conflicts, and search bounds

Static navigation only. A parent relationship does not transfer semantic
ownership and does not prove discoverability.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0008`
- Verification result: Every included route is present in the map and each edge resolves to direct source evidence.

## M34-E-0026 - Surface overlap and candidate-boundary inventory

- Status: `VERIFIED`
- Class: `DERIVED`
- Work package: `M34-WP3`
- Captured at UTC: 2026-07-19T07:33:12Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T07:33:12Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0022`
- Premise evidence ids: `M34-E-0005`, `M34-E-0006`, `M34-E-0007`, `M34-E-0008`, `M34-E-0009`, `M34-E-0010`, `M34-E-0013`, `M34-E-0019`, `M34-E-0020`, `M34-E-0021`, `M34-E-0022`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/implementation/m34/audit/reports/M34_WP3_surface_and_user_question_inventory.md`
- Symbol, route, section, schema, command, or fixture: `7. Duplicate Surface Candidates`; `8. Candidate Semantic Boundaries`
- Supporting artifact: `../reports/M34_WP3_surface_and_user_question_inventory.md`

### Factual observation

Ten surface pairs/groups expose similarly named claim areas, and nine
candidate semantic boundaries can be traced from current route claims and the
documented domain roles.

### Capture method

Compare surface output-claim labels and purposes. Retain each observed
distinction, call every overlap a candidate, and map claim categories to WP1
owner rules without deciding equivalence or ownership.

### Derived method

Cross-product comparison of the registered output-claim summaries, limited to
material visible overlap; boundary candidates use `M34-E-0013` and WP1 section
1.5 as constraints.

### Normative authority

- Authority level: `constitutional`
- Governing reference: `docs/implementation/M34_WP1_charter_and_audit_protocol.md::1.5 Ownership model`

### Limitations, conflicts, and search bounds

This is not a duplicate-concept finding, an owner ruling, or a redesign
proposal. Semantic identity remains unknown until WP5.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0008`
- Verification result: Every candidate cites two or more registered surfaces and preserves an observed distinction or explicit uncertainty.

## M34-E-0027 - WP3 route-level completeness assessment

- Status: `VERIFIED`
- Class: `DERIVED`
- Work package: `M34-WP3`
- Captured at UTC: 2026-07-19T07:33:12Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T07:33:12Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0022`
- Premise evidence ids: `M34-E-0017`, `M34-E-0018`, `M34-E-0019`, `M34-E-0020`, `M34-E-0021`, `M34-E-0022`, `M34-E-0023`, `M34-E-0024`, `M34-E-0025`, `M34-E-0026`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/implementation/m34/audit/reports/M34_WP3_surface_and_user_question_inventory.md`
- Symbol, route, section, schema, command, or fixture: `10. Inventory Completeness Assessment`; `11. Recommendation for WP5`
- Supporting artifact: `../reports/M34_WP3_surface_and_user_question_inventory.md`

### Factual observation

All 24 route pages are accounted for, all 22 included surfaces have every
requested WP3 classification, and all dynamic included surfaces have a named
frontend API boundary. Backend lineage, correctness, runtime behavior, and
component-level semantic variants remain explicitly incomplete.

### Capture method

Count route-universe records and verify one surface-inventory row, question
row, mode class, scope class, navigation placement, evidence reference, and
unknown field for every included route.

### Derived method

Reconcile `M34-E-0017` through `M34-E-0026`; completeness is limited to the
route-level WP3 deliverables and does not extend to M34 semantic readiness.

### Normative authority

- Authority level: `specification`
- Governing reference: `docs/implementation/M34_WP1_charter_and_audit_protocol.md::1.2 Scope`

### Limitations, conflicts, and search bounds

“Complete enough for WP5” is a work-package handoff conclusion, not M34 exit,
M34.1 GO, or proof of correctness.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0005`, `M34-R-0008`
- Verification result: Identifier counts, matrix coverage, and explicit exclusion/unknown accounting reproduced without dangling surface rows.

## M34-E-0028 - WP3 surfaces resolve to a bounded frontend read-contract population

- Status: `VERIFIED`
- Class: `DIRECT`
- Work package: `M34-WP4`
- Captured at UTC: 2026-07-19T08:02:10Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:02:10Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0023`, `M34-C-0047`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `frontend/lib/api.ts; frontend/lib/PortfolioContext.tsx; frontend/app/**/page.tsx; directly rendered portfolio-facing components`
- Symbol, route, section, schema, command, or fixture: exported `GET` client functions and their call sites for the frozen WP3 surfaces
- Supporting artifact: `../reports/M34_WP4_read_contract_and_lineage_inventory.md::3. Frontend to Backend Contract Map`

### Factual observation

The frozen WP3 surfaces and directly rendered components consume 43 unique
HTTP `GET` endpoints for material read claims. `/system-guide` reads static
route content, and `/goal-wizard` has no independent material read beyond the
shared `listPortfolios()` context.

### Capture method

Enumerate named client calls in frozen WP3 routes/components, resolve each to
its exported `frontend/lib/api.ts` path, deduplicate by method and route, and
record explicit static/no-independent-read boundaries.

### Derived method

`NONE`

### Normative authority

- Authority level: `specification`
- Governing reference: `docs/implementation/m34/audit/reports/M34_WP3_surface_and_user_question_inventory.md::2. Surface inventory`

### Limitations, conflicts, and search bounds

POST/PATCH/PUT/DELETE command responses and runtime-only contracts are not
reclassified as reads. No runtime payload was observed.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0009`
- Verification result: All 43 unique frontend GET mappings and both static/no-independent-read cases were reproduced from source.

## M34-E-0029 - Frontend reads map to explicit FastAPI handlers

- Status: `VERIFIED`
- Class: `DIRECT`
- Work package: `M34-WP4`
- Captured at UTC: 2026-07-19T08:02:10Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:02:10Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0040`, `M34-C-0043`, `M34-C-0044`, `M34-C-0045`, `M34-C-0046`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `backend/main.py`
- Symbol, route, section, schema, command, or fixture: 43 `@app.get` handlers matched to `M34-E-0028`
- Supporting artifact: `../reports/M34_WP4_read_contract_and_lineage_inventory.md::2. Read Contract Inventory`

### Factual observation

Every HTTP read in `M34-E-0028` resolves to an explicit FastAPI handler. The
inventoried decorators do not declare named response models; handlers return
ordinary dictionaries or lists, directly or from a service entry.

### Capture method

Match each exact client path to a `@app.get` decorator, inspect the handler
signature/body, and record its first service call or direct ORM/configuration
projection.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

Transport presence does not establish semantic correctness or field-level
runtime parity with the TypeScript interfaces.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0009`
- Verification result: Every client route matched one handler; method/path and first service/direct-read hop reproduced.

## M34-E-0030 - Portfolio, market, stock, watchlist, and configuration source paths

- Status: `VERIFIED`
- Class: `DIRECT`
- Work package: `M34-WP4`
- Captured at UTC: 2026-07-19T08:02:10Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:02:10Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0040`, `M34-C-0041`, `M34-C-0042`, `M34-C-0046`, `M34-C-0048`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `backend/main.py; backend/services/data_fetcher.py; backend/agents/chart_data.py; backend/models/database.py; backend/ai-model.json`
- Symbol, route, section, schema, command, or fixture: portfolio/holding/price/sector/watchlist/stock/history/consensus/settings GET handlers and direct helpers
- Supporting artifact: `../reports/M34_WP4_read_contract_and_lineage_inventory.md::2.1 Portfolio, market, instrument, and shared-scope contracts`

### Factual observation

The traced handlers read explicit Portfolio, PortfolioItem, Watchlist,
AgentCache, AnalysisCache, AnalysisHistory, Settings, MarketDataCache, and
related registry/configuration sources. Quote and chart helpers can use the
configured provider when cache/source policy permits.

### Capture method

Follow direct calls and ORM queries from the matched handlers into data
fetching/chart helpers and record the first concrete model, file, cache, or
provider boundary.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

No runtime branch, cache state, provider, or payload was selected or observed.
Analysis and market semantics were not assessed.

### Redaction and sensitivity

Configuration values, credentials, provider payloads, and personal data were
not inspected or retained.

### Verification record

- Review ids: `M34-R-0010`
- Verification result: Direct handler/helper/model/file paths reproduced for every contract in the stated family.

## M34-E-0031 - Snapshot, performance, and factor read lineage

- Status: `VERIFIED`
- Class: `DIRECT`
- Work package: `M34-WP4`
- Captured at UTC: 2026-07-19T08:02:10Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:02:10Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0040`, `M34-C-0042`, `M34-C-0043`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `backend/main.py; backend/services/analytics/quant_engine.py; backend/services/analytics/factor_engine.py; backend/models/database.py`
- Symbol, route, section, schema, command, or fixture: snapshot, performance-comparison, performance-stats, and factor-exposure GET paths
- Supporting artifact: `../reports/M34_WP4_read_contract_and_lineage_inventory.md::2.2 Snapshot, performance, and analytical contracts`

### Factual observation

Snapshot and performance reads source PortfolioSnapshot, BenchmarkPrice, and
SignalHistory rows before handler/service aggregation. Factor exposure reads
Portfolio and PortfolioItem rows and reaches market/agent inputs through the
data-fetcher boundary.

### Capture method

Trace each handler to its query sites and public analytics entry, stopping at
concrete persisted inputs, cache/provider boundaries, and response builders.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

Function bodies were inspected only for call/query lineage. Formulas, metric
meaning, and correctness were not assessed.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0010`
- Verification result: Handler, service, model, and response paths reproduced for all four analytical contract families.

## M34-E-0032 - Operations and optimizer read lineage

- Status: `VERIFIED`
- Class: `DIRECT`
- Work package: `M34-WP4`
- Captured at UTC: 2026-07-19T08:02:10Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:02:10Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0044`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `backend/main.py; backend/services/operations_center.py; backend/services/run_progress.py; backend/services/optimizer/strategy_profiles.py`
- Symbol, route, section, schema, command, or fixture: operations status/progress, optimizer history/detail, strategy-profile, persona, and legacy-decision GET paths
- Supporting artifact: `../reports/M34_WP4_read_contract_and_lineage_inventory.md::2.3 Operations Center and optimizer/intelligence contracts`

### Factual observation

Operations status composes explicit portfolio, snapshot, decision, optimizer,
recommendation, benchmark, regime, goal, and configuration sources. Optimizer
history/detail read OptimizerHistory and RecommendationSnapshot; progress reads
a per-process in-memory registry; profile/persona reads static and Portfolio
sources.

### Capture method

Inspect matched handlers, the operations-service public entry, model queries,
dynamic helper imports, and the run-progress/profile sources.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

Live optimizer POST responses and any execution behavior remain excluded.
Response-time history enrichment is recorded but not evaluated.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0010`
- Verification result: Observable handler/service/model/in-memory paths reproduced without command execution.

## M34-E-0033 - Decision-memory, shadow, attribution, comparison, and calibration lineage

- Status: `VERIFIED`
- Class: `DIRECT`
- Work package: `M34-WP4`
- Captured at UTC: 2026-07-19T08:02:10Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:02:10Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0043`, `M34-C-0044`, `M34-C-0045`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `backend/main.py; backend/services/analytics/attribution_engine.py; backend/services/analytics/human_vs_ai.py; backend/services/analytics/regime_attribution.py; backend/services/decision_memory/calibration.py; backend/services/evaluation/ideal_series.py`
- Symbol, route, section, schema, command, or fixture: decision-memory, attribution-summary, human-vs-AI, regime-attribution, calibration/history, shadow-performance, and AI-vs-human-timeline GET paths
- Supporting artifact: `../reports/M34_WP4_read_contract_and_lineage_inventory.md::2.3 Operations Center and optimizer/intelligence contracts`

### Factual observation

The paths reach explicit decision, recommendation, portfolio/shadow snapshot,
attribution, regime, optimizer, signal, agent-cache, grade/calibration,
benchmark, and settings sources through named services and handler joins.

### Capture method

Follow each matched handler into its public analytical service and record ORM
query/model references plus immediate shared-service dependencies.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

No formula, persistence side effect, historical claim, or semantic equivalence
was assessed.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0010`
- Verification result: Named service and model participation reproduced for every listed shared intelligence contract.

## M34-E-0034 - AI Evaluation endpoint and source lineage

- Status: `VERIFIED`
- Class: `DIRECT`
- Work package: `M34-WP4`
- Captured at UTC: 2026-07-19T08:02:10Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:02:10Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0041`, `M34-C-0043`, `M34-C-0045`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `backend/main.py; backend/services/evaluation/; backend/services/analytics/human_vs_ai.py`
- Symbol, route, section, schema, command, or fixture: scorecard, recommendation ledger/report, execution ledger/detail, scoreboard, opportunity-cost, trust-report, and shared three-portfolio paths
- Supporting artifact: `../reports/M34_WP4_read_contract_and_lineage_inventory.md::2.4 AI Evaluation contracts`

### Factual observation

The eight unique evaluation GET handlers, including the trust-report read,
delegate to named service entries.
Those services query or reuse explicit recommendation, grade, decision,
transaction, portfolio/shadow snapshot, benchmark, calibration, workspace,
settings, and shared analytical sources.

### Capture method

Match frontend evaluation calls to handlers, inspect the delegated public
service, record ORM query sites and directly invoked shared services, and stop
before formula or semantic assessment.

### Derived method

`NONE`

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

Service documentation is navigation context only; source queries/calls support
the observation. No grade or counterfactual meaning was verified.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0010`
- Verification result: All evaluation handler/service/source chains reproduced from repository source.

## M34-E-0035 - Current persistence-source catalogue for WP4 reads

- Status: `VERIFIED`
- Class: `DERIVED`
- Work package: `M34-WP4`
- Captured at UTC: 2026-07-19T08:02:10Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:02:10Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0040`, `M34-C-0041`, `M34-C-0042`, `M34-C-0043`, `M34-C-0044`, `M34-C-0045`, `M34-C-0046`, `M34-C-0048`
- Premise evidence ids: `M34-E-0030`, `M34-E-0031`, `M34-E-0032`, `M34-E-0033`, `M34-E-0034`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `backend/models/database.py; backend/ai-model.json; source paths identified by M34-E-0030 through M34-E-0034`
- Symbol, route, section, schema, command, or fixture: ORM `__tablename__` declarations and read-query participation
- Supporting artifact: `../reports/M34_WP4_read_contract_and_lineage_inventory.md::5. Persistence Source Inventory`

### Factual observation

Twenty-one ORM tables, one repository JSON configuration file, in-process
caches/registry, and configured provider boundaries participate in at least one
current WP4 read lineage. Each participation is listed without ranking or
semantic authority.

### Capture method

Reconcile direct model/query/file/in-memory/provider references from
`M34-E-0030` through `M34-E-0034` with ORM table declarations and deduplicate
by source identity.

### Derived method

Deterministic source-set union over `M34-E-0030` through `M34-E-0034`; a source
is included only when a traced contract directly references it.

### Normative authority

- Authority level: `NONE`
- Governing reference: `NONE`

### Limitations, conflicts, and search bounds

Participation does not prove canonical ownership, correctness, runtime use, or
complete source schemas. Provider boundaries are not persistence tables.

### Redaction and sensitivity

No rows, values, secrets, or provider payloads were inspected.

### Verification record

- Review ids: `M34-R-0010`
- Verification result: Source names, table identities, and at least one supporting traced read were reproduced.

## M34-E-0036 - Known response transformation and aggregation locations

- Status: `VERIFIED`
- Class: `DERIVED`
- Work package: `M34-WP4`
- Captured at UTC: 2026-07-19T08:02:10Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:02:10Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0043`, `M34-C-0044`, `M34-C-0045`, `M34-C-0047`
- Premise evidence ids: `M34-E-0028`, `M34-E-0029`, `M34-E-0030`, `M34-E-0031`, `M34-E-0032`, `M34-E-0033`, `M34-E-0034`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/implementation/m34/audit/reports/M34_WP4_read_contract_and_lineage_inventory.md`
- Symbol, route, section, schema, command, or fixture: `6. Transformation Inventory`
- Supporting artifact: `../reports/M34_WP4_read_contract_and_lineage_inventory.md`

### Factual observation

Each material contract family has recorded frontend, handler, or service
locations where response rows are selected, joined, grouped, filtered, or
reshaped before display.

### Capture method

Compare frontend consumers, handler bodies, and public service entries from the
premise evidence; record transformation location and kind without reproducing
or evaluating formulas.

### Derived method

One transformation entry is retained for each distinct observed composition
boundary across `M34-E-0028` through `M34-E-0034`.

### Normative authority

- Authority level: `specification`
- Governing reference: `docs/implementation/M34_WP1_charter_and_audit_protocol.md::1.2 Scope`

### Limitations, conflicts, and search bounds

No calculation, valuation, freshness, trust, or implementation-quality
judgment is contained in this evidence.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0011`
- Verification result: Every inventoried contract family has an explicit transformation location or an explicit direct/static projection.

## M34-E-0037 - Read lineage, cross-domain dependencies, and shared-contract candidates

- Status: `VERIFIED`
- Class: `DERIVED`
- Work package: `M34-WP4`
- Captured at UTC: 2026-07-19T08:02:10Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:02:10Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0043`, `M34-C-0044`, `M34-C-0045`, `M34-C-0047`
- Premise evidence ids: `M34-E-0028`, `M34-E-0029`, `M34-E-0030`, `M34-E-0031`, `M34-E-0032`, `M34-E-0033`, `M34-E-0034`, `M34-E-0035`, `M34-E-0036`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/implementation/m34/audit/reports/M34_WP4_read_contract_and_lineage_inventory.md`
- Symbol, route, section, schema, command, or fixture: `7. Read Lineage Map`; `8. Cross-domain Read Dependencies`; `9. Shared Contract Candidates`
- Supporting artifact: `../reports/M34_WP4_read_contract_and_lineage_inventory.md`

### Factual observation

The registered source chains produce one common transport pattern, seven
candidate consumer/dependency groupings, and twelve shared-contract candidates.
All owner labels and sharing relationships remain candidates.

### Capture method

Project each verified contract from surface to client call, handler, service,
source, transport, and presentation; group only exact reused endpoints or
directly observed source dependencies.

### Derived method

Deterministic projection over `M34-E-0028` through `M34-E-0036`; matching
labels without a shared endpoint/source chain are not merged.

### Normative authority

- Authority level: `constitutional`
- Governing reference: `docs/implementation/M34_WP1_charter_and_audit_protocol.md::1.5 Ownership model`

### Limitations, conflicts, and search bounds

The projection makes no ownership decision and does not assert semantic
identity, correctness, or trust.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0011`
- Verification result: Every dependency/candidate is backed by at least one verified contract chain and retains explicit classification limits.

## M34-E-0038 - WP4 read-contract completeness assessment

- Status: `VERIFIED`
- Class: `DERIVED`
- Work package: `M34-WP4`
- Captured at UTC: 2026-07-19T08:02:10Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:02:10Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0047`
- Premise evidence ids: `M34-E-0022`, `M34-E-0027`, `M34-E-0028`, `M34-E-0029`, `M34-E-0030`, `M34-E-0031`, `M34-E-0032`, `M34-E-0033`, `M34-E-0034`, `M34-E-0035`, `M34-E-0036`, `M34-E-0037`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/implementation/m34/audit/reports/M34_WP4_read_contract_and_lineage_inventory.md`
- Symbol, route, section, schema, command, or fixture: `11. Read Contract Completeness Assessment`; `12. Recommendation for WP5`
- Supporting artifact: `../reports/M34_WP4_read_contract_and_lineage_inventory.md`

### Factual observation

All frozen WP3 surfaces are accounted for; 43 unique material GET contracts
and one static content contract have client, handler/service, response, source,
transformation, candidate-owner, confidence, and unknown coverage sufficient
to begin WP5 semantic-authority verification.

### Capture method

Reconcile the frozen WP3 surface/output inventory against the unique contract
map and require a source/response/unknown entry for every material read claim.

### Derived method

Closed-population reconciliation of `M34-E-0022`, `M34-E-0027`, and
`M34-E-0028` through `M34-E-0037`; command-only responses remain explicit
exclusions rather than missing read contracts.

### Normative authority

- Authority level: `specification`
- Governing reference: `docs/implementation/M34_WP1_charter_and_audit_protocol.md::1.2 Scope`

### Limitations, conflicts, and search bounds

“Complete enough for WP5” is a work-package handoff conclusion only. It is not
proof of semantics, correctness, ownership, product readiness, M34 exit, or
M34.1 GO.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0011`
- Verification result: Surface, endpoint, service/source, transform, unknown, and explicit exclusion accounting reproduced without an untraced material WP3 read claim.

## M34-E-0039 - Platform constitution defines exclusive semantic domains and governance precedence

- Status: `VERIFIED`
- Class: `DOCUMENTATION`
- Work package: `M34-WP5`
- Captured at UTC: 2026-07-19T08:38:31Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:38:31Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0049`, `M34-C-0050`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/architecture/platform_architecture.md; docs/GLOSSARY.md`
- Symbol, route, section, schema, command, or fixture: constitution sections 6, 7, 11, and 12; Glossary `Domain`, `Platform Domains`, `Observer Plane`, and `Domain Constitution`
- Supporting artifact: `../reports/M34_WP5_semantic_authority_matrix.md::2. Governing authority and namespace result`

### Factual observation

The ratified constitution states that every concept has one domain home,
defines the nine exclusive domains and their responsibilities, makes
Experience the renderer and owner of no truth, ranks governing artifacts, and
designates the Glossary as the sole canonical vocabulary.

### Capture method

Read the ratified domain, dependency, governance, and vocabulary sections and
cross-check the domain names and selected canonical terms against the Glossary.

### Derived method

`NONE`

### Normative authority

- Authority level: `constitutional`
- Governing reference: `docs/architecture/platform_architecture.md::Constitution v1.1`

### Limitations, conflicts, and search bounds

This establishes normative ownership, not current implementation conformance.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0012`
- Verification result: Domain names, exclusive responsibilities, precedence rules, and Glossary authority reproduced directly from the constitution.

## M34-E-0040 - Frozen WP1 uses a different audit-domain owner vocabulary and mandates ARB return

- Status: `VERIFIED`
- Class: `DOCUMENTATION`
- Work package: `M34-WP5`
- Captured at UTC: 2026-07-19T08:38:31Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:38:31Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0049`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/implementation/M34_WP1_charter_and_audit_protocol.md`
- Symbol, route, section, schema, command, or fixture: sections 1.4, 1.5, 2, and 8
- Supporting artifact: `../reports/M34_WP5_semantic_authority_matrix.md::2. Governing authority and namespace result`

### Factual observation

WP1 assigns owner rules using Portfolio, Analytics, Market Data, Ledger,
Portfolio Intelligence, AI Evaluation, and Experience audit-domain names. It
also requires conflicts to remain visible and requires ARB return when frozen
governance materially conflicts, primary ownership cannot be resolved, or a
governance artifact needs reinterpretation.

### Capture method

Read the frozen evidence, ownership, corpus-domain, and stop-condition rules
and compare the exact names without treating them as aliases.

### Derived method

`NONE`

### Normative authority

- Authority level: `specification`
- Governing reference: `docs/implementation/M34_WP1_charter_and_audit_protocol.md`

### Limitations, conflicts, and search bounds

WP5 does not amend WP1 or decide whether the names were intended as aliases.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0012`
- Verification result: Owner table, conflict rule, allowed corpus names, and applicable stop conditions reproduced exactly.

## M34-E-0041 - Portfolio scope and ledger fact authority are explicitly separated

- Status: `VERIFIED`
- Class: `DOCUMENTATION`
- Work package: `M34-WP5`
- Captured at UTC: 2026-07-19T08:38:31Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:38:31Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0051`, `M34-C-0052`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/architecture/PORTFOLIO_DOMAIN_MODEL.md; docs/architecture/TRANSACTION_DOMAIN_MODEL.md; docs/decisions/ADR-001_TRANSACTION_LEDGER_SINGLE_SOURCE_OF_TRUTH.md; docs/decisions/ADR-002_NO_COMPENSATION_FOR_LEDGER_DEFECTS.md`
- Symbol, route, section, schema, command, or fixture: Portfolio sections 1-3 and 10; Transaction sections 1-5; ADR decisions
- Supporting artifact: `../reports/M34_WP5_semantic_authority_matrix.md::3.1 Portfolio, ledger, and market-observation claims`

### Factual observation

Portfolio is declared the strategy/accounting scope. Transactions are
immutable facts and the ledger is the source of truth; holdings, cash, and
snapshots are derived. Portfolio does not own market observations or private
calculation variants.

### Capture method

Reconcile explicit owns/never-owns, facts-versus-derivations, and
Portfolio/Transaction relationship statements.

### Derived method

`NONE`

### Normative authority

- Authority level: `architecture and ADR`
- Governing reference: `PORTFOLIO_DOMAIN_MODEL.md; TRANSACTION_DOMAIN_MODEL.md; ADR-001; ADR-002`

### Limitations, conflicts, and search bounds

The Portfolio domain model is lower than the platform constitution and does
not itself establish which of the nine platform domains owns Portfolio
identity.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0012`
- Verification result: Scope, immutable fact, derivation, and prohibited-ownership statements reproduced without inspecting formulas.

## M34-E-0042 - Market Intelligence owns canonical observations and their failure semantics

- Status: `VERIFIED`
- Class: `DOCUMENTATION`
- Work package: `M34-WP5`
- Captured at UTC: 2026-07-19T08:38:31Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:38:31Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0053`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/architecture/MARKET_DATA_PLATFORM.md; docs/architecture/platform_architecture.md`
- Symbol, route, section, schema, command, or fixture: Market Data sections 2, 7, 8, 10-12; Platform Architecture section 6.2
- Supporting artifact: `../reports/M34_WP5_semantic_authority_matrix.md::3.1 Portfolio, ledger, and market-observation claims`

### Factual observation

Market Intelligence owns canonical prices, histories, calendars, rates,
regimes, observation moments, provenance, availability, and explicit freshness.
Providers are witnesses; Asset Foundation owns final identity/classification.

### Capture method

Read responsibility, canonical observation, validation, quality, failure, and
cache-boundary sections.

### Derived method

`NONE`

### Normative authority

- Authority level: `constitutional and architecture`
- Governing reference: `platform_architecture.md::6.2; MARKET_DATA_PLATFORM.md`

### Limitations, conflicts, and search bounds

The document describes target authority, not which runtime provider/cache
branch supplied a WP4 response.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0012`
- Verification result: Observation, provenance, freshness, metadata, and failure responsibilities reproduced.

## M34-E-0043 - Portfolio Intelligence owns derived measures while accounting rules own their frozen inputs

- Status: `VERIFIED`
- Class: `DOCUMENTATION`
- Work package: `M34-WP5`
- Captured at UTC: 2026-07-19T08:38:31Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:38:31Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0051`, `M34-C-0052`, `M34-C-0054`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/architecture/platform_architecture.md; docs/architecture/PORTFOLIO_DOMAIN_MODEL.md; docs/investment/PORTFOLIO_CALCULATION_RULES.md; docs/architecture/ARCHITECTURE.md`
- Symbol, route, section, schema, command, or fixture: constitutional section 6.5; Portfolio sections 2 and 10; calculation semantic sections; current factor/analytics sections
- Supporting artifact: `../reports/M34_WP5_semantic_authority_matrix.md::3. Semantic Authority Matrix`

### Factual observation

The constitution assigns valuation, performance, benchmark, risk, exposure,
attribution, and canonical derived-measure semantics to Portfolio Intelligence.
Ledger/accounting supplies facts and frozen semantic inputs. Current
implementation documentation defines selected factor/regime concepts but is
lower authority.

### Capture method

Compare explicit domain responsibility with Portfolio scope, accounting
semantic authority, and current implementation terminology. Do not inspect or
reproduce calculations.

### Derived method

`NONE`

### Normative authority

- Authority level: `constitutional and domain constitution`
- Governing reference: `platform_architecture.md::6.5; PORTFOLIO_CALCULATION_RULES.md`

### Limitations, conflicts, and search bounds

WP1 calls this owner `ANALYTICS`; no approved alias mapping was found.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0012`
- Verification result: Derived-measure owner and source-domain input boundaries reproduced without calculation evaluation.

## M34-E-0044 - Decision Intelligence owns beliefs, recommendations, plans, policy, and decision records

- Status: `VERIFIED`
- Class: `DOCUMENTATION`
- Work package: `M34-WP5`
- Captured at UTC: 2026-07-19T08:38:31Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:38:31Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0055`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/architecture/platform_architecture.md; docs/investment/OPTIMIZER_PHILOSOPHY.md; docs/architecture/ARCHITECTURE.md`
- Symbol, route, section, schema, command, or fixture: constitutional section 6.6; optimizer pipeline, human-decision, evaluation, and invariants sections; current optimizer/persona/decision-memory descriptions
- Supporting artifact: `../reports/M34_WP5_semantic_authority_matrix.md::3.3 Decision, evaluation, operations, and explanatory claims`

### Factual observation

Decision Intelligence exclusively owns beliefs, recommendations, plans,
policy envelope, and decision records. Later stages cannot mutate earlier
objects, AI never mutates accounting, and human choice remains sovereign.

### Capture method

Read the constitutional owner statement and the optimizer domain
constitution's stage, immutability, and human-decision rules.

### Derived method

`NONE`

### Normative authority

- Authority level: `constitutional and domain constitution`
- Governing reference: `platform_architecture.md::6.6; OPTIMIZER_PHILOSOPHY.md`

### Limitations, conflicts, and search bounds

This does not establish that a current legacy response is a canonical plan or
that a legacy decision is an authorized approval.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0012`
- Verification result: Exclusive concepts, stage separation, immutability, and human sovereignty reproduced.

## M34-E-0045 - Trust and Evaluation owns grades, calibration, counterfactuals, and trust vocabulary

- Status: `VERIFIED`
- Class: `DOCUMENTATION`
- Work package: `M34-WP5`
- Captured at UTC: 2026-07-19T08:38:31Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:38:31Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0056`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/architecture/platform_architecture.md; docs/investment/OPTIMIZER_PHILOSOPHY.md; docs/investment/EXECUTION_INTELLIGENCE_UX.md; docs/implementation/AI_EVALUATION_IMPLEMENTATION_PLAN.md; docs/GLOSSARY.md`
- Symbol, route, section, schema, command, or fixture: Trust domain; three lenses; three portfolios; grades; opportunity cost; calibration; as-of/degraded modes; observer-plane terms
- Supporting artifact: `../reports/M34_WP5_semantic_authority_matrix.md::3.3 Decision, evaluation, operations, and explanatory claims`

### Factual observation

Trust & Evaluation is a read-only observer plane that owns grades,
calibration, counterfactual tracks, comparisons, and trust vocabulary. The
design defines independent belief/execution/outcome lenses and the Ideal,
AI, actual, Gap A/B, and opportunity-cost concepts.

### Capture method

Reconcile constitutional ownership, optimizer evaluation philosophy,
approved UX object definitions, implementation-plan invariants, and matching
Glossary entries.

### Derived method

`NONE`

### Normative authority

- Authority level: `constitutional, domain constitution, and approved design`
- Governing reference: `platform_architecture.md::6.7; OPTIMIZER_PHILOSOPHY.md; EXECUTION_INTELLIGENCE_UX.md`

### Limitations, conflicts, and search bounds

No grade, comparison, or counterfactual calculation was evaluated. WP1 uses
the different label `AI_EVALUATION`.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0012`
- Verification result: Observer-plane owner, concept definitions, and read-only constraints reproduced.

## M34-E-0046 - Closed M32/M33 decisions deny canonical plan and approval authority to legacy reads

- Status: `VERIFIED`
- Class: `DOCUMENTATION`
- Work package: `M34-WP5`
- Captured at UTC: 2026-07-19T08:38:31Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:38:31Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0055`, `M34-C-0056`, `M34-C-0057`
- Premise evidence ids: `NONE`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/implementation/M32_EPIC_CLOSEOUT.md; docs/implementation/M33_11_supabase_auth_security_state_and_assurance_proof_of_concept.md; docs/engineering/DECISION_LOG.md`
- Symbol, route, section, schema, command, or fixture: M32 final readiness/active path; M33.11 decision and exact effects
- Supporting artifact: `../reports/M34_WP5_semantic_authority_matrix.md::3.3 Decision, evaluation, operations, and explanatory claims`

### Factual observation

M32 closed with canonical execution planning NO-GO and retained the legacy
response as the active product path without upgrading it. M33 ended
`STOP_M33_RUNTIME`, keeps legacy behavior outside approval authority, and
forbids attribution of legacy activity to future actors.

### Capture method

Read only the final decisions, active/legacy-path descriptions, terminal
effects, and non-adoption statements.

### Derived method

`NONE`

### Normative authority

- Authority level: `closed milestone decision`
- Governing reference: `M32_EPIC_CLOSEOUT.md; M33_11...md; DECISION_LOG.md`

### Limitations, conflicts, and search bounds

Pure M32/M33 contracts were not considered for runtime reuse and no reopen
criteria were evaluated.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0012`, `M34-R-0014`
- Verification result: Canonical-plan NO-GO, runtime stop, legacy non-authority, and non-adoption effects reproduced.

## M34-E-0047 - Canonical Glossary coverage is incomplete for observable portfolio claims

- Status: `VERIFIED`
- Class: `DERIVED`
- Work package: `M34-WP5`
- Captured at UTC: 2026-07-19T08:38:31Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:38:31Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0049`, `M34-C-0050`
- Premise evidence ids: `M34-E-0023`, `M34-E-0039`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/GLOSSARY.md; docs/implementation/m34/audit/reports/M34_WP3_surface_and_user_question_inventory.md`
- Symbol, route, section, schema, command, or fixture: all exact `##` Glossary headings reconciled to WP5 `SA01`-`SA40`
- Supporting artifact: `../reports/M34_WP5_semantic_authority_matrix.md::6. Shared Terminology Inventory`

### Factual observation

Seven of the forty semantic claim families have a directly applicable exact
Glossary definition. Portfolio Snapshot, Recommendation Snapshot, Shadow
Portfolio, Ideal Portfolio, AI Portfolio, Gap A/B, Opportunity Cost,
Recommendation Grade, Ledger, and Canonical Ledger Event are present. Most
visible nouns, including Portfolio, Return, Performance, Risk, Attribution,
Contribution, Freshness, Execution Plan, Human Decision, Trust Report, and
Watchlist, have no exact canonical entry.

### Capture method

Enumerate every exact level-two heading in `docs/GLOSSARY.md`; compare
case-insensitively against the concept and shared-term names required by the
forty closed claim families; accept a match only when the definition directly
governs the family rather than merely containing the word in prose.

### Derived method

Closed set comparison of the WP5 concept names against exact Glossary
definitions, with related definitions such as Gap A/B retained only for the
specific comparison family they govern.

### Normative authority

- Authority level: `canonical vocabulary`
- Governing reference: `platform_architecture.md::12; docs/GLOSSARY.md`

### Limitations, conflicts, and search bounds

An absent exact heading does not prove the word appears nowhere in prose. It
proves there is no exact canonical definition under the constitution's
one-term/one-home rule. WP5 does not author missing entries.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0012`, `M34-R-0014`
- Verification result: Complete heading enumeration and claim-family mapping reproduced; seven directly governed families and all listed gaps confirmed.

## M34-E-0048 - Forty semantic claim families cover every frozen observable output

- Status: `VERIFIED`
- Class: `DERIVED`
- Work package: `M34-WP5`
- Captured at UTC: 2026-07-19T08:38:31Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:38:31Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0049`, `M34-C-0058`
- Premise evidence ids: `M34-E-0023`, `M34-E-0027`, `M34-E-0038`, `M34-E-0039`, `M34-E-0040`, `M34-E-0041`, `M34-E-0042`, `M34-E-0043`, `M34-E-0044`, `M34-E-0045`, `M34-E-0046`, `M34-E-0047`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/implementation/m34/audit/reports/M34_WP5_semantic_authority_matrix.md`
- Symbol, route, section, schema, command, or fixture: section 3, `SA01` through `SA40`
- Supporting artifact: `../reports/M34_WP5_semantic_authority_matrix.md`

### Factual observation

Every visible output-claim group in the frozen 22-surface WP3 matrix and its
WP4 read lineage maps to exactly one of forty semantic claim families. Each
family records WP1 and constitutional candidates, competing authority,
definition source, result, confidence, and unknowns.

### Capture method

Reconcile every WP3 surface-inventory output list against the forty matrix
rows; require every family to cite governing authority or explicit unknown and
retain the WP4 source boundary without recalculating it.

### Derived method

Closed-population projection over `M34-E-0023`, `M34-E-0027`, `M34-E-0038`,
and the authority evidence `M34-E-0039` through `M34-E-0047`.

### Normative authority

- Authority level: `specification`
- Governing reference: `M34_WP1_charter_and_audit_protocol.md::1.5 Ownership model`

### Limitations, conflicts, and search bounds

Grouping proves inventory coverage, not correctness or semantic equivalence
of fields within a family.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0013`
- Verification result: Forty unique rows, complete WP3 output reconciliation, and required authority fields reproduced.

## M34-E-0049 - One-owner, conflict, terminology, dependency, violation-candidate, and unknown inventories

- Status: `VERIFIED`
- Class: `DERIVED`
- Work package: `M34-WP5`
- Captured at UTC: 2026-07-19T08:38:31Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:38:31Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0049`, `M34-C-0058`
- Premise evidence ids: `M34-E-0039`, `M34-E-0040`, `M34-E-0046`, `M34-E-0047`, `M34-E-0048`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/implementation/m34/audit/reports/M34_WP5_semantic_authority_matrix.md`
- Symbol, route, section, schema, command, or fixture: sections 4 through 9
- Supporting artifact: `../reports/M34_WP5_semantic_authority_matrix.md`

### Factual observation

The forty families produce 9 aligned, 19 provisionally mapped, 7 conflicted,
2 stopped-authority, and 3 unknown-owner results. The report separately
records nine conflict groups, fifteen shared-term groups, one cross-domain
dependency projection, thirteen authority-violation candidates, and eight
unknown categories without choosing a winner.

### Capture method

Classify only explicit owner/result fields from `SA01`-`SA40`; group repeated
conflict premises and shared words while retaining every affected row id and
authority limitation.

### Derived method

Deterministic count and grouping over `M34-E-0048` under the constitutional
domain responsibilities and WP1 conflict rules.

### Normative authority

- Authority level: `constitutional and specification`
- Governing reference: `platform_architecture.md::6,11,12; M34 WP1 sections 1.4,1.5,8`

### Limitations, conflicts, and search bounds

Authority-violation candidates are inventory records in the report, not
findings, severity classifications, or dispositions.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0014`
- Verification result: Result counts, conflict/term/dependency groups, candidates, and unknown categories reproduced with no inferred owner.

## M34-E-0050 - WP5 authority completeness requires ARB return before WP6

- Status: `VERIFIED`
- Class: `DERIVED`
- Work package: `M34-WP5`
- Captured at UTC: 2026-07-19T08:38:31Z
- Captured by: Lead Technical Auditor
- Verified by: Lead Technical Auditor
- Verified at UTC: 2026-07-19T08:38:31Z
- Repository revision: `531b01b17a34955a65dd45f5e9386763652938ab`
- Environment: `STATIC_REPOSITORY`
- Corpus ids: `M34-C-0049`, `M34-C-0058`
- Premise evidence ids: `M34-E-0040`, `M34-E-0046`, `M34-E-0047`, `M34-E-0048`, `M34-E-0049`
- Linked finding ids: `NONE`
- Supersedes: `NONE`
- Superseded by: `NONE`

### Source locator

- Path or environment locator: `docs/implementation/m34/audit/reports/M34_WP5_semantic_authority_matrix.md`
- Symbol, route, section, schema, command, or fixture: sections 10 and 11
- Supporting artifact: `../reports/M34_WP5_semantic_authority_matrix.md`

### Factual observation

Surface/claim and read-lineage coverage are complete, but the WP1-to-
constitution mapping, exact canonical vocabulary, cross-domain owners, and
legacy execution/decision meanings are insufficient for full WP6. WP1 stop
conditions require affected work to return to the Architecture Review Board.

### Capture method

Apply WP1 stop conditions 1, 5, and 11 to the verified namespace conflict,
unknown owners, missing vocabulary, and closed M32/M33 authority boundaries;
do not convert the result into an M34 exit decision.

### Derived method

Readiness intersection of `M34-E-0040`, `M34-E-0046`, `M34-E-0047`,
`M34-E-0048`, and `M34-E-0049`: full WP6 requires one owner and one governing
definition for every included claim; any unresolved mandatory dimension
returns false.

### Normative authority

- Authority level: `specification`
- Governing reference: `M34_WP1_charter_and_audit_protocol.md::8. Stop conditions`

### Limitations, conflicts, and search bounds

This is a WP5 handoff recommendation and escalation, not an ARB decision,
finding disposition, M34 exit, or M34.1 decision.

### Redaction and sensitivity

`NONE`

### Verification record

- Review ids: `M34-R-0015`
- Verification result: Completeness dimensions, failed WP6 prerequisites, stop-condition applicability, and bounded ARB questions reproduced.
