# M34 Corpus Register

**Status:** Active. M34-WP2 product evidence, the complete M34-WP3 route-level
surface inventory, the bounded M34-WP4 read-contract lineage areas, and the
M34-WP5 semantic-authority corpus are registered. WP5 returned unresolved
authority namespace and ownership questions to the Architecture Review Board.

**Governing protocol:**
`../../../M34_WP1_charter_and_audit_protocol.md`

**Working-artifact rules:** `../README.md`

## Use

This register records both approved corpus areas and discovered artifacts.
M34-WP2 seeded the Experience, Documentation, and Governance items needed for
its product-evidence boundary. M34-WP3 added the bounded route universe,
portfolio-facing routes, shared navigation, and frontend API-contract boundary.
M34-WP4 added the current backend read-contract, source-lineage, persistence,
configuration, and frontend-transformation areas needed for WP5. M34-WP5 adds
the governing constitution, domain authority, canonical-vocabulary, and closed
M32/M33 boundary artifacts needed for its authority assessment. The remaining
WP1 correctness and runtime corpus is not yet fully audited.

Allowed record kinds are `AREA` and `ARTIFACT`. Allowed domains are
`EXPERIENCE`, `PORTFOLIO`, `ANALYTICS`, `MARKET_DATA`, `LEDGER`,
`PORTFOLIO_INTELLIGENCE`, `AI_EVALUATION`, `DOCUMENTATION`, `TESTS`,
`GOVERNANCE`, and `TOOLING_GENERATED` under the bounded WP1 rule.

Allowed statuses are `DECLARED`, `DISCOVERED`, `VERIFICATION_PENDING`,
`VERIFIED_IN_SCOPE`, `VERIFIED_OUT_OF_SCOPE`, `COVERAGE_COMPLETE`, and
`DISPUTED`.

## Record template

```markdown
## M34-C-NNNN - <area or artifact title>

- Record kind: <AREA | ARTIFACT>
- Status: <corpus status>
- Domain: <allowed domain>
- Parent corpus id: <M34-C-NNNN | NONE>
- Work package discovered: <M34-WP# | NONE for protocol-declared area>
- Path anchor or pattern: <repository-relative locator | SEMANTIC_BOUNDARY>
- Scope granularity: <directory | file | symbol | route | schema | document section | semantic area>
- Inclusion basis: <WP1 section/rule>
- Exclusion boundary: <explicit boundary | NONE>
- Discovered by / UTC: <identity and timestamp | PENDING>
- Verified by / UTC: <identity and timestamp | PENDING>
- Review ids: <sorted M34-R-NNNN ids | PENDING>
- Child corpus ids: <sorted M34-C-NNNN ids | NONE>
- Evidence ids: <sorted M34-E-NNNN ids | NONE>
- Finding ids: <sorted M34-F-NNNN ids | NONE>

### Scope statement

<Why this area/artifact does or does not satisfy WP1 section 1.2.>

### Search and traversal bounds

<Imports, calls, schemas, configuration, lineage, documentation references,
patterns, and explicit limits used to assess coverage. PENDING until discovery.>

### Coverage notes

<Known children, shared-file symbol boundary, unresolved coverage, or NONE.>
```

## Records

## M34-C-0001 - Experience product-evidence area

- Record kind: `AREA`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `NONE`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `frontend/`
- Scope granularity: `semantic area`
- Inclusion basis: WP1 sections 1.2 and 2.2
- Exclusion boundary: Product entry points, route surfaces, navigation, exposed claims, portfolio-context behavior, and frontend contract links only; no semantic-correctness audit
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0001`, `M34-R-0002`, `M34-R-0004`, `M34-R-0005`, `M34-R-0006`, `M34-R-0007`, `M34-R-0008`
- Child corpus ids: `M34-C-0004`, `M34-C-0005`, `M34-C-0006`, `M34-C-0007`, `M34-C-0008`, `M34-C-0009`, `M34-C-0010`, `M34-C-0011`, `M34-C-0012`, `M34-C-0013`, `M34-C-0014`, `M34-C-0015`, `M34-C-0016`, `M34-C-0017`, `M34-C-0022`, `M34-C-0023`, `M34-C-0024`, `M34-C-0025`, `M34-C-0026`, `M34-C-0027`, `M34-C-0028`, `M34-C-0029`, `M34-C-0030`, `M34-C-0031`, `M34-C-0032`, `M34-C-0033`, `M34-C-0034`, `M34-C-0035`, `M34-C-0036`, `M34-C-0037`, `M34-C-0038`, `M34-C-0039`
- Evidence ids: `M34-E-0001`, `M34-E-0002`, `M34-E-0003`, `M34-E-0004`, `M34-E-0005`, `M34-E-0006`, `M34-E-0007`, `M34-E-0008`, `M34-E-0009`, `M34-E-0010`, `M34-E-0014`, `M34-E-0015`, `M34-E-0017`, `M34-E-0018`, `M34-E-0019`, `M34-E-0020`, `M34-E-0021`, `M34-E-0022`, `M34-E-0023`, `M34-E-0024`, `M34-E-0025`, `M34-E-0026`, `M34-E-0027`
- Finding ids: `NONE`

### Scope statement

Current portfolio-facing routes, inbound links, shared navigation,
repository-exposed user tasks, route-level output claims, scope, and frontend
contract links answer the WP2 and WP3 inventory questions.

### Search and traversal bounds

Bounded to all 24 `frontend/app/**/page.tsx` routes at the audited revision,
the registered shared navigation/context artifacts, explicit links, imported
client API functions, and the WP2 product-instrumentation search.

### Coverage notes

WP3 route-level surface coverage is complete for the audited revision. This
area is not `COVERAGE_COMPLETE` for later backend semantic, contract,
degraded-state, accessibility, or correctness work packages.

## M34-C-0002 - Documentation product-evidence area

- Record kind: `AREA`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `DOCUMENTATION`
- Parent corpus id: `NONE`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `docs/` and `frontend/app/system-guide/page.tsx`
- Scope granularity: `semantic area`
- Inclusion basis: WP1 sections 1.2 and 2.9
- Exclusion boundary: Declared portfolio purpose, capabilities, tasks, and navigation only
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0003`, `M34-R-0004`
- Child corpus ids: `M34-C-0018`, `M34-C-0020`, `M34-C-0021`
- Evidence ids: `M34-E-0011`, `M34-E-0013`, `M34-E-0016`
- Finding ids: `NONE`

### Scope statement

These artifacts declare current product tasks or domain meaning relevant to
whether route distribution represents a product problem.

### Search and traversal bounds

Bounded to the registered documents and the user-research search recorded in
`M34-E-0016`.

### Coverage notes

No claim of complete M34 documentation coverage.

## M34-C-0003 - Governance product-capability area

- Record kind: `AREA`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `GOVERNANCE`
- Parent corpus id: `NONE`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `docs/architecture/ROADMAP.md`
- Scope granularity: `semantic area`
- Inclusion basis: WP1 sections 1.2 and 2.11
- Exclusion boundary: Current declared portfolio capabilities only; no roadmap redesign
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0003`
- Child corpus ids: `M34-C-0019`
- Evidence ids: `M34-E-0012`
- Finding ids: `NONE`

### Scope statement

The roadmap records which portfolio and analytical capabilities the product
claims as current.

### Search and traversal bounds

Only capability-status sections relevant to present portfolio tasks.

### Coverage notes

No roadmap decision or status is changed by WP2.

## M34-C-0004 - Authenticated application shell

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `frontend/components/AppShell.tsx`
- Scope granularity: `file`
- Inclusion basis: Establishes shared navigation and portfolio context for current journeys
- Exclusion boundary: Authentication correctness and M33 identity authority
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0001`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0001`
- Finding ids: `NONE`

### Scope statement

The shell determines which shared product controls surround authenticated
portfolio routes.

### Search and traversal bounds

Authentication redirect and render composition only.

### Coverage notes

No token, account, identity, or authorization audit.

## M34-C-0005 - Global navigation

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `frontend/components/Navbar.tsx`
- Scope granularity: `file`
- Inclusion basis: Defines global entry points, route grouping, and portfolio selection
- Exclusion boundary: Styling and unrelated admin behavior
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0001`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0002`, `M34-E-0014`
- Finding ids: `NONE`

### Scope statement

Global entry points and current hub membership directly determine the WP2
navigation map.

### Search and traversal bounds

`NAV_MAIN`, brand link, active-route matching, and portfolio selector only.

### Coverage notes

Desktop and mobile render from the same navigation arrays.

## M34-C-0006 - Shared active-portfolio context

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `frontend/lib/PortfolioContext.tsx`
- Scope granularity: `file`
- Inclusion basis: Defines selection continuity across current journeys
- Exclusion boundary: Portfolio API semantics and identity
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0001`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0003`, `M34-E-0014`
- Finding ids: `NONE`

### Scope statement

The artifact supplies one shared selected-portfolio state to multiple product
routes.

### Search and traversal bounds

Selection initialization, persistence, and exposed context only.

### Coverage notes

No judgment of storage, error handling, or correctness.

## M34-C-0007 - Portfolio secondary navigation

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `frontend/components/PortfolioTabs.tsx`
- Scope granularity: `file`
- Inclusion basis: Defines the current three-route portfolio hub
- Exclusion boundary: Visual design
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0001`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0004`, `M34-E-0014`
- Finding ids: `NONE`

### Scope statement

The tabs are direct evidence for both consolidation and retained route
separation.

### Search and traversal bounds

Tab destinations and active-route behavior only.

### Coverage notes

No usability claim is made from the component's presence.

## M34-C-0008 - Post-login legacy dashboard

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `frontend/app/page.tsx`
- Scope granularity: `file`
- Inclusion basis: Current landing route and cross-portfolio entry surface
- Exclusion boundary: Price and aggregation correctness
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0002`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0005`
- Finding ids: `NONE`

### Scope statement

The root page is both the login destination and the navbar brand destination.

### Search and traversal bounds

Displayed task, portfolio scope, and outbound stock links only.

### Coverage notes

No semantic evaluation of heatmap values.

## M34-C-0009 - Portfolio overview route

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `frontend/app/portfolio/page.tsx`
- Scope granularity: `file`
- Inclusion basis: Primary portfolio entry and exposed tasks
- Exclusion boundary: Calculation, transaction, freshness, and failure correctness
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0002`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0006`, `M34-E-0014`
- Finding ids: `NONE`

### Scope statement

The route exposes current portfolio maintenance, inspection, and drill-down
tasks.

### Search and traversal bounds

Labels, controls, route links, and major displayed sections only.

### Coverage notes

No task value or frequency is inferred.

## M34-C-0010 - Portfolio performance route

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `frontend/app/performance/page.tsx`
- Scope granularity: `file`
- Inclusion basis: Current change/performance journey and cross-hub attribution entry
- Exclusion boundary: Return, snapshot, benchmark, and attribution correctness
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0002`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0007`, `M34-E-0014`
- Finding ids: `NONE`

### Scope statement

The route exposes snapshot, return, benchmark, history, and explanation tasks.

### Search and traversal bounds

User-facing headings, actions, states, and explicit links only.

### Coverage notes

No semantic judgment of displayed measures.

## M34-C-0011 - Portfolio analytics route

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `frontend/app/analytics/page.tsx`
- Scope granularity: `file`
- Inclusion basis: Current quantitative-investigation journey
- Exclusion boundary: Analytics calculations, terminology, freshness, and correctness
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0002`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0008`, `M34-E-0014`
- Finding ids: `NONE`

### Scope statement

The route exposes performance, benchmark, drawdown, signal, and allocation
investigation tasks.

### Search and traversal bounds

User-facing sections, filters, and route context only.

### Coverage notes

No interpretation of analytical validity.

## M34-C-0012 - Portfolio factor drill-down route

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `frontend/app/portfolio/[id]/factors/page.tsx`
- Scope granularity: `file`
- Inclusion basis: Current portfolio drill-down and return path
- Exclusion boundary: Factor calculations and interpretation
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0002`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0009`, `M34-E-0014`
- Finding ids: `NONE`

### Scope statement

This dynamic route is explicitly linked from the portfolio overview and
retains the Portfolio tabs.

### Search and traversal bounds

Entry, heading, empty state, breadcrumb, and tabs only.

### Coverage notes

Uses a route portfolio id rather than only the shared active id; no UX or
correctness conclusion is drawn.

## M34-C-0013 - Portfolio Intelligence route

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `frontend/app/portfolio-intelligence/page.tsx`
- Scope granularity: `file`
- Inclusion basis: Current decision-investigation journey
- Exclusion boundary: Execution authority and intelligence semantics
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0002`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0010`, `M34-E-0014`
- Finding ids: `NONE`

### Scope statement

The route is a portfolio-scoped investigation surface reached from the AI
Operations Center rather than the Portfolio tabs.

### Search and traversal bounds

Entry context, headings, major panels, selected-portfolio dependency, and
breadcrumb only.

### Coverage notes

No M32/M33 runtime or execution conclusion.

## M34-C-0014 - Portfolio holdings table links

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `frontend/components/PortfolioTable.tsx`
- Scope granularity: `symbol`
- Inclusion basis: Outbound investigation path from a holding to stock detail
- Exclusion boundary: Table values, calculations, and actions
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0002`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0009`
- Finding ids: `NONE`

### Scope statement

Symbol links establish an explicit current investigation journey.

### Search and traversal bounds

`/stock/[symbol]` links only.

### Coverage notes

No table-content audit.

## M34-C-0015 - Stock detail route

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `frontend/app/stock/[symbol]/page.tsx`
- Scope granularity: `file`
- Inclusion basis: Current investigation destination linked from portfolio surfaces
- Exclusion boundary: Stock-analysis semantics and data correctness
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0002`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0009`
- Finding ids: `NONE`

### Scope statement

The route supplies a back-navigation-based detail destination from portfolio
holdings and the legacy dashboard.

### Search and traversal bounds

Heading, breadcrumb, and major section names only.

### Coverage notes

No analysis-content audit.

## M34-C-0016 - Operations Center link to Portfolio Intelligence

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `frontend/components/operations-center/OperationsCenter.tsx`
- Scope granularity: `symbol`
- Inclusion basis: Explicit inbound link to Portfolio Intelligence
- Exclusion boundary: Operations Center behavior and optimizer
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0002`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0010`
- Finding ids: `NONE`

### Scope statement

The artifact establishes the current parent hub for Portfolio Intelligence.

### Search and traversal bounds

Header links only.

### Coverage notes

No AI/optimizer audit.

## M34-C-0017 - Login landing route

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `frontend/app/login/page.tsx`
- Scope granularity: `symbol`
- Inclusion basis: Establishes the first authenticated destination
- Exclusion boundary: Authentication implementation and M33 authority
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0001`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0001`
- Finding ids: `NONE`

### Scope statement

Successful login routes the current journey to `/`.

### Search and traversal bounds

Post-login navigation only.

### Coverage notes

No credential or session audit.

## M34-C-0018 - In-product System Guide

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `DOCUMENTATION`
- Parent corpus id: `M34-C-0002`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `frontend/app/system-guide/page.tsx`
- Scope granularity: `document section`
- Inclusion basis: Documents intended portfolio navigation and tasks
- Exclusion boundary: Guide correctness outside portfolio/product evidence
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0003`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0011`
- Finding ids: `NONE`

### Scope statement

The guide explicitly describes Portfolio as a center with three sub-tabs and
lists the task of each.

### Search and traversal bounds

Navigation overview, stock-detail journey, and Portfolio Intelligence entry
description only.

### Coverage notes

Documentation evidence does not establish actual user behavior.

## M34-C-0019 - Portfolio capability roadmap

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `GOVERNANCE`
- Parent corpus id: `M34-C-0003`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `docs/architecture/ROADMAP.md`
- Scope granularity: `document section`
- Inclusion basis: Records current claimed portfolio capabilities
- Exclusion boundary: Future roadmap design and status changes
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0003`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0012`
- Finding ids: `NONE`

### Scope statement

Current capability declarations establish breadth, not user value or
correctness.

### Search and traversal bounds

Portfolio Engine, Performance Analytics, Execution Intelligence, AI
Evaluation, and current Portfolio Intelligence sections.

### Coverage notes

No roadmap reconciliation in WP2.

## M34-C-0020 - Portfolio domain responsibilities

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `DOCUMENTATION`
- Parent corpus id: `M34-C-0002`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `docs/architecture/PORTFOLIO_DOMAIN_MODEL.md`
- Scope granularity: `document section`
- Inclusion basis: Defines portfolio-scoped jobs and the cross-portfolio Wealth distinction
- Exclusion boundary: Architecture redesign and implementation claims
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0003`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0013`
- Finding ids: `NONE`

### Scope statement

The document supplies authoritative declared meaning for portfolio-level and
whole-financial-picture questions.

### Search and traversal bounds

Philosophy, responsibilities, identity, and Wealth hierarchy sections only.

### Coverage notes

No assessment of implementation conformance.

## M34-C-0021 - Canonical domain vocabulary

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `DOCUMENTATION`
- Parent corpus id: `M34-C-0002`
- Work package discovered: `M34-WP2`
- Path anchor or pattern: `docs/GLOSSARY.md`
- Scope granularity: `document section`
- Inclusion basis: Defines Portfolio Intelligence and Experience Platform roles
- Exclusion boundary: Terminology audit outside the WP2 product case
- Discovered by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-17T11:33:15Z
- Review ids: `M34-R-0003`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0013`
- Finding ids: `NONE`

### Scope statement

The glossary distinguishes domain meaning from how a person meets the
product.

### Search and traversal bounds

Domain and Platform Domains entries only.

### Coverage notes

No terminology finding is created in WP2.

## M34-C-0022 - Frontend route-page universe

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP3`
- Path anchor or pattern: `frontend/app/**/page.tsx`
- Scope granularity: `directory pattern`
- Inclusion basis: WP1 sections 1.2 and 2.2; bounded universe for route-level portfolio surfaces
- Exclusion boundary: Layouts and embedded components are dependencies only; no semantic or calculation audit
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Review ids: `M34-R-0005`, `M34-R-0008`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0017`, `M34-E-0023`, `M34-E-0024`, `M34-E-0025`, `M34-E-0026`, `M34-E-0027`
- Finding ids: `NONE`

### Scope statement

The pattern supplies the reproducible population against which route-level
surface completeness is measured.

### Search and traversal bounds

Every `page.tsx` beneath `frontend/app`, plus imported navigation,
portfolio-context, and API-contract dependencies needed for classification.

### Coverage notes

Twenty-four route pages were enumerated; 22 were included and two were
explicitly excluded from the portfolio surface inventory.

## M34-C-0023 - Frontend portfolio-facing API contract boundary

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP3`
- Path anchor or pattern: `frontend/lib/api.ts`
- Scope granularity: `symbol set`
- Inclusion basis: WP1 section 2.2; links surface inputs and actions to current client contracts
- Exclusion boundary: Backend implementation, calculations, persistence, and correctness
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Review ids: `M34-R-0006`, `M34-R-0007`, `M34-R-0009`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0022`, `M34-E-0028`
- Finding ids: `NONE`

### Scope statement

Only functions imported by the 22 included surfaces and their HTTP method/path
declarations are inventoried as linked contracts.

### Search and traversal bounds

Named imports from included routes and directly rendered host components;
response fields and backend handlers are not followed in WP3.

### Coverage notes

Sufficient as the handoff boundary for later semantic lineage work, not as
proof of source authority.

## M34-C-0024 - AI Evaluation hub navigation shell

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP3`
- Path anchor or pattern: `frontend/app/ai-analytics/(hub)/layout.tsx`; `frontend/components/evaluation/EvaluationTabs.tsx`
- Scope granularity: `symbol set`
- Inclusion basis: Establishes the parent and sibling relationship of AI Evaluation surfaces
- Exclusion boundary: Evaluation semantics and AI system telemetry
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Review ids: `M34-R-0007`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0018`, `M34-E-0020`
- Finding ids: `NONE`

### Scope statement

The route group wraps nine portfolio-scoped evaluation routes and renders six
primary tab destinations plus a system-telemetry link.

### Search and traversal bounds

Route-group composition, tab destinations, and active-state matching only.

### Coverage notes

`/ai-analytics/system` is outside this shell and is separately classified
`VERIFIED_OUT_OF_SCOPE` for WP3.

## M34-C-0025 - AI Evaluation scorecard route

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `AI_EVALUATION`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP3`
- Path anchor or pattern: `frontend/app/ai-analytics/(hub)/page.tsx`
- Scope granularity: `route`
- Inclusion basis: Portfolio-scoped evaluation claims relevant to questions 3-5
- Exclusion boundary: Metric computation and validity
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Review ids: `M34-R-0007`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0020`
- Finding ids: `NONE`

### Scope statement

The `/ai-analytics` route presents belief, execution, and outcome evaluation
lenses for the selected portfolio.

### Search and traversal bounds

Purpose comments, headings, visible question labels, dependencies, links, and
API call only.

### Coverage notes

No evaluation result is judged.

## M34-C-0026 - AI Evaluation recommendations ledger route

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `AI_EVALUATION`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP3`
- Path anchor or pattern: `frontend/app/ai-analytics/(hub)/recommendations/page.tsx`
- Scope granularity: `route`
- Inclusion basis: Portfolio-scoped recommendation-history and investigation claims
- Exclusion boundary: Recommendation and counterfactual semantics
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Review ids: `M34-R-0007`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0020`
- Finding ids: `NONE`

### Scope statement

The route lists selected-portfolio recommendation records and links to one
report card.

### Search and traversal bounds

Route purpose, filters, outbound record link, API call, and output labels.

### Coverage notes

No legacy decision authority is inferred.

## M34-C-0027 - AI Evaluation recommendation report route

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `AI_EVALUATION`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP3`
- Path anchor or pattern: `frontend/app/ai-analytics/(hub)/recommendations/[id]/page.tsx`
- Scope granularity: `route`
- Inclusion basis: Portfolio- and record-scoped plan/outcome explanation
- Exclusion boundary: Plan, outcome, shadow, and benchmark correctness
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Review ids: `M34-R-0007`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0020`
- Finding ids: `NONE`

### Scope statement

The route presents one recommendation in plan, what-happened, and outcome
sections.

### Search and traversal bounds

Route ids, breadcrumb, section headings, API call, and visible claim labels.

### Coverage notes

No adoption of recommendation or execution semantics.

## M34-C-0028 - AI Evaluation execution ledger route

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `AI_EVALUATION`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP3`
- Path anchor or pattern: `frontend/app/ai-analytics/(hub)/execution/page.tsx`
- Scope granularity: `route`
- Inclusion basis: Portfolio-scoped recorded-decision outcome claims
- Exclusion boundary: Execution runtime, authority, and grading correctness
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Review ids: `M34-R-0007`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0020`
- Finding ids: `NONE`

### Scope statement

The route lists existing decision/evaluation records and links to one detail
record.

### Search and traversal bounds

Purpose, headings, period controls, record links, API call, and empty state.

### Coverage notes

The term “execution” is inventoried as current vocabulary and does not reopen
M32 or M33.

## M34-C-0029 - AI Evaluation execution detail route

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `AI_EVALUATION`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP3`
- Path anchor or pattern: `frontend/app/ai-analytics/(hub)/execution/[id]/page.tsx`
- Scope granularity: `route`
- Inclusion basis: Portfolio- and record-scoped plan-versus-actual explanation
- Exclusion boundary: Execution runtime, fulfillment, and delta correctness
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Review ids: `M34-R-0007`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0020`
- Finding ids: `NONE`

### Scope statement

The route presents one existing decision record's planned/actual fields and
warnings.

### Search and traversal bounds

Route ids, breadcrumb, headings, API call, and output labels only.

### Coverage notes

No transaction or execution authority is attributed.

## M34-C-0030 - AI Evaluation human-versus-AI route

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `AI_EVALUATION`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP3`
- Path anchor or pattern: `frontend/app/ai-analytics/(hub)/human-vs-ai/page.tsx`
- Scope granularity: `route`
- Inclusion basis: Portfolio-scoped comparative outcome claims
- Exclusion boundary: Scoreboard and counterfactual correctness
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Review ids: `M34-R-0007`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0020`
- Finding ids: `NONE`

### Scope statement

The route compares recorded human and AI outcomes and links to opportunity
cost.

### Search and traversal bounds

Purpose comment, headings, segment labels, link, period, and API call.

### Coverage notes

No judgment of comparative validity.

## M34-C-0031 - AI Evaluation opportunity-cost route

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `AI_EVALUATION`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP3`
- Path anchor or pattern: `frontend/app/ai-analytics/(hub)/opportunity-cost/page.tsx`
- Scope granularity: `route`
- Inclusion basis: Portfolio-scoped counterfactual investigation claims
- Exclusion boundary: Counterfactual and causal correctness
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Review ids: `M34-R-0007`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0020`
- Finding ids: `NONE`

### Scope statement

The route presents counterfactual divergence values, a waterfall, and system
deferrals.

### Search and traversal bounds

Purpose comment, breadcrumb, headings, warnings, links, period, and API call.

### Coverage notes

No claim that counterfactual value is realized value.

## M34-C-0032 - AI Evaluation portfolio-comparison route

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `AI_EVALUATION`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP3`
- Path anchor or pattern: `frontend/app/ai-analytics/(hub)/portfolios/page.tsx`
- Scope granularity: `route`
- Inclusion basis: Portfolio-scoped comparative value and risk claims
- Exclusion boundary: Shadow, index, return, gap, and risk correctness
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Review ids: `M34-R-0007`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0020`
- Finding ids: `NONE`

### Scope statement

The route compares Ideal, AI, and user portfolio series and two named gaps.

### Search and traversal bounds

Purpose, headings, period controls, API call, labels, and documented scope
notes only.

### Coverage notes

Deferred page features are recorded as unavailable, not fabricated inventory.

## M34-C-0033 - AI Evaluation attribution route

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `AI_EVALUATION`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP3`
- Path anchor or pattern: `frontend/app/ai-analytics/(hub)/attribution/page.tsx`
- Scope granularity: `route`
- Inclusion basis: Portfolio-scoped return-source explanation
- Exclusion boundary: Attribution calculation and causal correctness
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Review ids: `M34-R-0007`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0020`
- Finding ids: `NONE`

### Scope statement

The route presents return-attribution views and explicit unavailable states.

### Search and traversal bounds

Purpose comment, tab labels, headings, API calls, warnings, and outbound link.

### Coverage notes

No calculation was inspected.

## M34-C-0034 - Operations Center route and composed surface

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `PORTFOLIO_INTELLIGENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP3`
- Path anchor or pattern: `frontend/app/operations-center/page.tsx`; `frontend/components/operations-center/OperationsCenter.tsx`
- Scope granularity: `route and host component`
- Inclusion basis: Portfolio-scoped status, trust, and investigation surface
- Exclusion boundary: Optimizer correctness, execution, and runtime adoption
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Review ids: `M34-R-0007`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0019`
- Finding ids: `NONE`

### Scope statement

The route binds the active portfolio to a composed MUJI/Quant status surface,
analysis command, and advanced investigation links.

### Search and traversal bounds

Route scope states, host inputs/actions, major panel labels, direct links, and
API calls only.

### Coverage notes

Embedded cards remain part of this host surface for WP3.

## M34-C-0035 - Optimizer route

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `PORTFOLIO_INTELLIGENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP3`
- Path anchor or pattern: `frontend/app/optimizer/page.tsx`
- Scope granularity: `route`
- Inclusion basis: Portfolio-scoped recommendation, investigation, and legacy decision-label surface
- Exclusion boundary: Optimizer redesign, execution, M32/M33 reopening, and calculation inspection
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Review ids: `M34-R-0007`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0019`
- Finding ids: `NONE`

### Scope statement

The route displays analysis/recommendation sections, history, policy/persona
context, and existing decision controls for the active portfolio.

### Search and traversal bounds

Imports, route context, major headings, links, API calls, and visible action
labels only; calculation and presentation logic were not audited.

### Coverage notes

Inventory does not confer approval or execution authority.

## M34-C-0036 - Goal wizard route

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `PORTFOLIO_INTELLIGENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP3`
- Path anchor or pattern: `frontend/app/goal-wizard/page.tsx`; `frontend/components/goal/GoalWizard.tsx`
- Scope granularity: `route and host component`
- Inclusion basis: Writes portfolio-facing goal/profile context
- Exclusion boundary: Goal semantics, recommendation use, projections, and advice
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Review ids: `M34-R-0007`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0019`
- Finding ids: `NONE`

### Scope statement

The route captures and persists a selected portfolio's goal profile and
returns to AI Operations.

### Search and traversal bounds

Route context, stated non-advice boundary, displayed fields, save action, and
API call only.

### Coverage notes

The route does not directly answer one of the five M34 read questions.

## M34-C-0037 - Watchlist route with portfolio buy action

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP3`
- Path anchor or pattern: `frontend/app/watchlist/page.tsx`
- Scope granularity: `route`
- Inclusion basis: Instrument investigation surface with a selected-portfolio write boundary
- Exclusion boundary: Watchlist/analysis correctness and transaction semantics
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Review ids: `M34-R-0006`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0021`
- Finding ids: `NONE`

### Scope statement

The route reads and mutates global watchlist state, links to stock detail, and
uses the active portfolio only as a buy destination.

### Search and traversal bounds

Route inputs, headings, table claims, links, buy action, and API imports only.

### Coverage notes

Mixed scope is retained explicitly rather than normalized.

## M34-C-0038 - Settings route with portfolio-facing configuration

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP3`
- Path anchor or pattern: `frontend/app/settings/page.tsx`
- Scope granularity: `route sections`
- Inclusion basis: System-wide settings materially affect portfolio-facing optimizer and analysis claims
- Exclusion boundary: Settings correctness, policy ownership, and provider adoption
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Review ids: `M34-R-0006`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0021`
- Finding ids: `NONE`

### Scope statement

The route exposes portfolio/sector limits and related system configuration but
does not directly answer a current portfolio read question.

### Search and traversal bounds

Page purpose, portfolio/sector/data-management labels, and imported API
contracts only.

### Coverage notes

General provider settings are retained as context, not audited.

## M34-C-0039 - AI system telemetry route

- Record kind: `ARTIFACT`
- Status: `VERIFIED_OUT_OF_SCOPE`
- Domain: `AI_EVALUATION`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP3`
- Path anchor or pattern: `frontend/app/ai-analytics/system/page.tsx`
- Scope granularity: `route`
- Inclusion basis: Accounted route in the complete frontend page universe
- Exclusion boundary: System-wide AI operational telemetry with no portfolio scope or portfolio read claim
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T07:33:12Z
- Review ids: `M34-R-0005`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0017`
- Finding ids: `NONE`

### Scope statement

The route presents AI system health, model/layer telemetry, cost, latency,
tokens, reliability, and recent activity without selected-portfolio context.

### Search and traversal bounds

Route imports, absence of `usePortfolio`, headings, and route-group boundary.

### Coverage notes

Recorded out of scope to prevent repeated discovery. The login route is
already registered as `M34-C-0017` and is likewise excluded from the WP3
surface inventory after its entry role is accounted for.

## M34-C-0040 - Portfolio read-contract backend area

- Record kind: `AREA`
- Status: `COVERAGE_COMPLETE`
- Domain: `PORTFOLIO`
- Parent corpus id: `NONE`
- Work package discovered: `M34-WP4`
- Path anchor or pattern: `backend/main.py; backend/models/database.py; backend/services/portfolio_snapshots.py`
- Scope granularity: `symbol set`
- Inclusion basis: WP1 sections 1.2 and 2.3; current scope, holding, sector, snapshot, persona, and portfolio configuration reads
- Exclusion boundary: Writes, calculation correctness, portfolio redesign, and semantic ownership decisions
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T08:02:10Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T08:02:10Z
- Review ids: `M34-R-0009`, `M34-R-0010`
- Child corpus ids: `M34-C-0046`
- Evidence ids: `M34-E-0029`, `M34-E-0030`, `M34-E-0031`, `M34-E-0035`
- Finding ids: `NONE`

### Scope statement

The area contains the current portfolio-scoped handlers, ORM sources, and
snapshot projections consumed by the frozen WP3 surfaces.

### Search and traversal bounds

Only `GET` handlers and directly reached helpers/models behind the WP3 client
calls were followed. Write endpoints and correctness rules were not audited.

### Coverage notes

All material WP3 portfolio read calls resolve to an inventoried handler and
source boundary. Mixed-domain dependencies remain separately registered.

## M34-C-0041 - Ledger inputs to portfolio-facing reads

- Record kind: `AREA`
- Status: `COVERAGE_COMPLETE`
- Domain: `LEDGER`
- Parent corpus id: `NONE`
- Work package discovered: `M34-WP4`
- Path anchor or pattern: `backend/models/database.py::PortfolioItem, Transaction; portfolio-facing read symbols in backend/main.py and backend/services/evaluation/`
- Scope granularity: `symbol set`
- Inclusion basis: WP1 sections 1.2 and 2.6; holding and transaction facts observable in current read lineage
- Exclusion boundary: Write behavior, accounting correctness, repair, execution adoption, and ledger redesign
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T08:02:10Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T08:02:10Z
- Review ids: `M34-R-0010`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0030`, `M34-E-0034`, `M34-E-0035`
- Finding ids: `NONE`

### Scope statement

The area records current `PortfolioItem` inputs to holdings/sector reads and
`Transaction` inputs reached by evaluation detail projections.

### Search and traversal bounds

ORM query references reached from inventoried `GET` handlers only. Transaction
creation and stopped execution-runtime concepts were excluded.

### Coverage notes

Source participation is recorded without deciding whether a ledger fact is
used correctly.

## M34-C-0042 - Market-data read lineage area

- Record kind: `AREA`
- Status: `COVERAGE_COMPLETE`
- Domain: `MARKET_DATA`
- Parent corpus id: `NONE`
- Work package discovered: `M34-WP4`
- Path anchor or pattern: `backend/services/data_fetcher.py; backend/services/market_data/; backend/agents/chart_data.py; backend/models/database.py::MarketDataCache, BenchmarkPrice`
- Scope granularity: `symbol set`
- Inclusion basis: WP1 sections 1.2 and 2.5; quote, history, chart, benchmark, cache, and provider lineage used by WP3 surfaces
- Exclusion boundary: Provider adoption, runtime provider observation, freshness/correctness judgment, and market-data redesign
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T08:02:10Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T08:02:10Z
- Review ids: `M34-R-0010`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0030`, `M34-E-0031`, `M34-E-0035`
- Finding ids: `NONE`

### Scope statement

This area captures cache/provider and benchmark source paths observable behind
portfolio prices, stock charts, factors, performance, and downstream reads.

### Search and traversal bounds

Static call and model references only; no provider request or runtime cache
inspection was performed.

### Coverage notes

Provider selection at runtime remains unknown wherever source code permits
more than one path.

## M34-C-0043 - Analytics read-contract area

- Record kind: `AREA`
- Status: `COVERAGE_COMPLETE`
- Domain: `ANALYTICS`
- Parent corpus id: `NONE`
- Work package discovered: `M34-WP4`
- Path anchor or pattern: `backend/services/analytics/; backend/services/benchmark_service.py; analytics GET symbols in backend/main.py`
- Scope granularity: `directory and symbol set`
- Inclusion basis: WP1 sections 1.2 and 2.4; performance, factor, attribution, comparison, regime, and calibration read lineage
- Exclusion boundary: Formula/correctness assessment, analytics rewrite, and semantic ownership decisions
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T08:02:10Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T08:02:10Z
- Review ids: `M34-R-0010`, `M34-R-0011`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0029`, `M34-E-0031`, `M34-E-0033`, `M34-E-0034`, `M34-E-0035`, `M34-E-0036`, `M34-E-0037`
- Finding ids: `NONE`

### Scope statement

The area contains the current analytical service entries and persisted inputs
that produce portfolio-facing response dictionaries.

### Search and traversal bounds

Public service entries invoked by inventoried handlers, their ORM queries, and
their immediate shared-service dependencies. Mathematical bodies were not
assessed.

### Coverage notes

Enough lineage is present for WP5 field-level semantic verification; current
correctness is not asserted.

## M34-C-0044 - Portfolio Intelligence read-contract area

- Record kind: `AREA`
- Status: `COVERAGE_COMPLETE`
- Domain: `PORTFOLIO_INTELLIGENCE`
- Parent corpus id: `NONE`
- Work package discovered: `M34-WP4`
- Path anchor or pattern: `backend/services/operations_center.py; backend/services/decision_memory/; backend/services/run_progress.py; optimizer/intelligence GET symbols in backend/main.py`
- Scope granularity: `directory and symbol set`
- Inclusion basis: WP1 sections 1.2 and 2.7; operations status, optimizer history, decision memory, shadow, attribution, and calibration reads
- Exclusion boundary: Optimizer redesign, execution adoption, command responses, and M32/M33 reopening
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T08:02:10Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T08:02:10Z
- Review ids: `M34-R-0010`, `M34-R-0011`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0029`, `M34-E-0032`, `M34-E-0033`, `M34-E-0035`, `M34-E-0036`, `M34-E-0037`
- Finding ids: `NONE`

### Scope statement

This area contains the existing read projections behind Operations Center,
Optimizer, and Portfolio Intelligence claims identified by WP3.

### Search and traversal bounds

Only `GET` response paths and their immediate model/service sources. Live
optimizer command outputs and execution behavior were excluded.

### Coverage notes

Legacy decision and execution-labelled sources are inventoried as current
reads only; `STOP_M33_RUNTIME` remains controlling.

## M34-C-0045 - AI Evaluation read-contract area

- Record kind: `AREA`
- Status: `COVERAGE_COMPLETE`
- Domain: `AI_EVALUATION`
- Parent corpus id: `NONE`
- Work package discovered: `M34-WP4`
- Path anchor or pattern: `backend/services/evaluation/; evaluation GET symbols in backend/main.py; backend/services/analytics/human_vs_ai.py::compute_scoreboard`
- Scope granularity: `directory and symbol set`
- Inclusion basis: WP1 sections 1.2 and 2.8; scorecard, ledgers, report/detail, scoreboard, opportunity cost, three-portfolio, attribution, and trust-report reads
- Exclusion boundary: Grade/formula correctness, AI redesign, execution adoption, and final ownership decisions
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T08:02:10Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T08:02:10Z
- Review ids: `M34-R-0010`, `M34-R-0011`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0029`, `M34-E-0033`, `M34-E-0034`, `M34-E-0035`, `M34-E-0036`, `M34-E-0037`
- Finding ids: `NONE`

### Scope statement

The area contains the current service and source graph for the nine WP3 AI
Evaluation routes and the Operations Center evaluation summaries.

### Search and traversal bounds

Endpoint-to-public-service calls, ORM query sites, and immediate shared
analytics dependencies. No calculations, tests, or runtime payloads were
evaluated.

### Coverage notes

All eight unique evaluation endpoints, including the trust-report read, plus shared attribution and
three-portfolio reads are accounted for.

## M34-C-0046 - Portfolio-facing configuration read artifacts

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `PORTFOLIO`
- Parent corpus id: `M34-C-0040`
- Work package discovered: `M34-WP4`
- Path anchor or pattern: `backend/main.py::_get_ai_settings, _get_analysis_sources, _get_sector_limits, _get_portfolio_settings, _get_optimizer_layers, _get_optimizer_fallback; backend/ai-model.json; backend/models/database.py::Settings`
- Scope granularity: `symbol set and file`
- Inclusion basis: WP1 sections 1.2, 2.3, and 2.12; configuration read contracts visible on WP3 surfaces
- Exclusion boundary: Configuration writes, policy correctness, secret values, and ownership decisions
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T08:02:10Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T08:02:10Z
- Review ids: `M34-R-0009`, `M34-R-0010`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0029`, `M34-E-0030`, `M34-E-0035`
- Finding ids: `NONE`

### Scope statement

The artifact set supplies saved/default portfolio, sector, AI,
analysis-source, and optimizer configuration projected onto Settings and Stock
surfaces.

### Search and traversal bounds

GET handlers, helper reads, static model catalogue, response types, and
`Settings` query references only.

### Coverage notes

Domain classification reflects the portfolio-facing audit boundary and is not
a final ownership ruling for each setting.

## M34-C-0047 - Frontend read-response transformation boundary

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `EXPERIENCE`
- Parent corpus id: `M34-C-0001`
- Work package discovered: `M34-WP4`
- Path anchor or pattern: `frontend/lib/PortfolioContext.tsx; frontend/lib/api.ts; frontend/lib/analytics-transformers.ts; frontend/app/**/page.tsx; directly rendered portfolio-facing components`
- Scope granularity: `symbol set`
- Inclusion basis: WP1 sections 1.2 and 2.2; current client calls, DTOs, selection, joining, filtering, and display projections
- Exclusion boundary: UI redesign, semantic correctness, formula judgment, and component implementation quality
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T08:02:10Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T08:02:10Z
- Review ids: `M34-R-0009`, `M34-R-0011`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0028`, `M34-E-0036`, `M34-E-0037`, `M34-E-0038`
- Finding ids: `NONE`

### Scope statement

The symbol set establishes which client response types are consumed and where
the current frontend composes or reshapes them before display.

### Search and traversal bounds

Named imports/calls from frozen WP3 routes and directly rendered components,
plus their response interfaces and transformation helpers.

### Coverage notes

Presentation transformation is recorded without transferring semantic
ownership to Experience.

## M34-C-0048 - Stock and watchlist analysis read artifacts

- Record kind: `AREA`
- Status: `COVERAGE_COMPLETE`
- Domain: `MARKET_DATA`
- Parent corpus id: `NONE`
- Work package discovered: `M34-WP4`
- Path anchor or pattern: `stock/watchlist GET symbols in backend/main.py; backend/agents/; backend/services/registry_lookup.py; backend/models/database.py::Watchlist, AgentCache, AnalysisCache, AnalysisHistory`
- Scope granularity: `symbol set and directory`
- Inclusion basis: WP1 sections 1.2, 2.5, 2.7, and 2.8; instrument claims feeding portfolio-facing investigation surfaces
- Exclusion boundary: Agent/AI correctness, registry redesign, provider adoption, and write/job behavior
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T08:02:10Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T08:02:10Z
- Review ids: `M34-R-0010`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0030`, `M34-E-0035`
- Finding ids: `NONE`

### Scope statement

The area records current quick-analysis, history, consensus, watchlist,
registry, cache, and agent/provider read paths used by WP3 surfaces.

### Search and traversal bounds

GET handlers and directly invoked helper/model paths only. Analysis commands,
jobs, and semantic quality were not audited.

### Coverage notes

The `MARKET_DATA` register classification keeps the observed instrument-data
boundary explicit; final ownership of AI analysis claims remains unknown.

## M34-C-0049 - Semantic authority and vocabulary governance area

- Record kind: `AREA`
- Status: `COVERAGE_COMPLETE`
- Domain: `GOVERNANCE`
- Parent corpus id: `NONE`
- Work package discovered: `M34-WP5`
- Path anchor or pattern: `docs/architecture/platform_architecture.md; docs/GLOSSARY.md; frozen WP1 ownership and stop rules; registered domain-authority artifacts`
- Scope granularity: `semantic area`
- Inclusion basis: WP1 sections 1.2, 1.5, 2.9, and 2.11; WP5 one-concept/one-owner and canonical-definition verification
- Exclusion boundary: Calculation correctness, architecture redesign, domain creation, vocabulary authoring, and ownership disposition
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Review ids: `M34-R-0012`, `M34-R-0013`, `M34-R-0014`, `M34-R-0015`
- Child corpus ids: `M34-C-0050`, `M34-C-0051`, `M34-C-0052`, `M34-C-0053`, `M34-C-0054`, `M34-C-0055`, `M34-C-0056`, `M34-C-0057`, `M34-C-0058`
- Evidence ids: `M34-E-0039`, `M34-E-0040`, `M34-E-0047`, `M34-E-0048`, `M34-E-0049`, `M34-E-0050`
- Finding ids: `NONE`

### Scope statement

This area contains the highest available authority needed to map every frozen
WP3/WP4 observable claim to one semantic owner and one definition source.

### Search and traversal bounds

Platform Constitution domain/governance/vocabulary sections; frozen WP1
ownership/stop rules; domain constitutions and technical authority documents;
canonical Glossary exact headings; M32/M33 terminal authority decisions; and
the closed 40-family WP5 reconciliation.

### Coverage notes

Coverage is complete for the WP5 authority question. Authority itself is not
complete: the WP1/constitutional namespace conflict and unowned or unregistered
concepts are preserved and escalated.

## M34-C-0050 - Platform constitution and canonical Glossary

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `GOVERNANCE`
- Parent corpus id: `M34-C-0049`
- Work package discovered: `M34-WP5`
- Path anchor or pattern: `docs/architecture/platform_architecture.md; docs/GLOSSARY.md`
- Scope granularity: `document sections`
- Inclusion basis: Platform domain ownership, governance hierarchy, and canonical-vocabulary authority
- Exclusion boundary: Constitutional amendment and glossary authoring
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Review ids: `M34-R-0012`, `M34-R-0014`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0039`, `M34-E-0047`
- Finding ids: `NONE`

### Scope statement

The ratified constitution defines the exclusive domain homes, document
precedence, and one-term/one-meaning rule; the Glossary is the sole canonical
vocabulary.

### Search and traversal bounds

Constitution sections 2, 4-7, 10-12 and every exact level-two heading in
`docs/GLOSSARY.md`.

### Coverage notes

The bounded heading reconciliation is evidence of vocabulary coverage, not a
proposal to add missing terms.

## M34-C-0051 - Portfolio scope and strategy authority documents

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `PORTFOLIO`
- Parent corpus id: `M34-C-0049`
- Work package discovered: `M34-WP5`
- Path anchor or pattern: `docs/architecture/PORTFOLIO_DOMAIN_MODEL.md`
- Scope granularity: `document sections`
- Inclusion basis: Portfolio identity, scope, accounting boundary, benchmark, policy, risk, analytics, and Wealth boundary declarations
- Exclusion boundary: Portfolio redesign and formula evaluation
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Review ids: `M34-R-0012`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0041`, `M34-E-0043`
- Finding ids: `NONE`

### Scope statement

The document establishes Portfolio as strategy, policy, and accounting scope
and states what it owns or must consume from more specific domains.

### Search and traversal bounds

Sections 1-3, 5-7, 10, and 12 only; future product design was excluded.

### Coverage notes

Scope authority is explicit, while mapping the Portfolio model to one of the
nine constitutional domains remains unresolved.

## M34-C-0052 - Ledger and accounting semantic authority documents

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `LEDGER`
- Parent corpus id: `M34-C-0049`
- Work package discovered: `M34-WP5`
- Path anchor or pattern: `docs/architecture/TRANSACTION_DOMAIN_MODEL.md; docs/investment/PORTFOLIO_CALCULATION_RULES.md; docs/decisions/ADR-001_TRANSACTION_LEDGER_SINGLE_SOURCE_OF_TRUTH.md; docs/decisions/ADR-002_NO_COMPENSATION_FOR_LEDGER_DEFECTS.md`
- Scope granularity: `document set`
- Inclusion basis: Ledger facts, replay, holdings/cash/cost authority, and frozen accounting meaning behind observable claims
- Exclusion boundary: Formula execution or correctness assessment
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Review ids: `M34-R-0012`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0041`, `M34-E-0043`
- Finding ids: `NONE`

### Scope statement

These artifacts define immutable transaction facts, derived state, accounting
scope, and the governing semantic rules consumed by Portfolio Intelligence.

### Search and traversal bounds

Ownership/responsibility, fact-versus-snapshot, relationship-to-Portfolio,
NAV/return terminology, and invariant sections only. No formula was tested.

### Coverage notes

The documents support authority boundaries but do not prove current outputs.

## M34-C-0053 - Market-observation semantic authority document

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `MARKET_DATA`
- Parent corpus id: `M34-C-0049`
- Work package discovered: `M34-WP5`
- Path anchor or pattern: `docs/architecture/MARKET_DATA_PLATFORM.md`
- Scope granularity: `document sections`
- Inclusion basis: Price, observation time, provenance, availability, freshness, benchmark, metadata, and regime source authority
- Exclusion boundary: Provider adoption, adapter design, runtime evidence, and market-value correctness
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Review ids: `M34-R-0012`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0042`
- Finding ids: `NONE`

### Scope statement

The document defines Market Intelligence's canonical observation and failure
boundary without making a provider authoritative.

### Search and traversal bounds

Responsibilities, normalization, validation, provider quality, failure, and
caching sections only.

### Coverage notes

No current provider/cache branch was selected.

## M34-C-0054 - Portfolio-derived-measure authority documents

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `ANALYTICS`
- Parent corpus id: `M34-C-0049`
- Work package discovered: `M34-WP5`
- Path anchor or pattern: `docs/architecture/platform_architecture.md::6.5 Portfolio Intelligence; docs/architecture/PORTFOLIO_DOMAIN_MODEL.md::10 Analytics Boundary; docs/investment/PORTFOLIO_CALCULATION_RULES.md; docs/architecture/ARCHITECTURE.md::analytics and factor sections`
- Scope granularity: `document section set`
- Inclusion basis: Valuation, performance, benchmark, risk, exposure, factor, contribution, and attribution semantic authority
- Exclusion boundary: Calculation evaluation and analytics redesign
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Review ids: `M34-R-0012`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0043`
- Finding ids: `NONE`

### Scope statement

The sources assign derived-measure meaning to constitutional Portfolio
Intelligence while recording current analytical vocabulary and accounting
inputs.

### Search and traversal bounds

Owner/responsibility statements and named current concept definitions only;
mathematical bodies were not assessed.

### Coverage notes

The WP1 `ANALYTICS` label-to-constitutional-owner mapping remains unapproved.

## M34-C-0055 - Decision Intelligence semantic authority documents

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `PORTFOLIO_INTELLIGENCE`
- Parent corpus id: `M34-C-0049`
- Work package discovered: `M34-WP5`
- Path anchor or pattern: `docs/architecture/platform_architecture.md::6.6 Decision Intelligence; docs/investment/OPTIMIZER_PHILOSOPHY.md; docs/architecture/ARCHITECTURE.md::optimizer and decision-memory sections`
- Scope granularity: `document section set`
- Inclusion basis: Belief, recommendation, plan, policy, decision-record, persona, factor-context, and decision-memory authority
- Exclusion boundary: Optimizer redesign, recommendation correctness, execution adoption, and approval authority
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Review ids: `M34-R-0012`, `M34-R-0014`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0044`, `M34-E-0046`
- Finding ids: `NONE`

### Scope statement

The constitution and optimizer philosophy assign beliefs, recommendations,
plans, policy, and decision records to Decision Intelligence.

### Search and traversal bounds

Pipeline roles, evaluation separation, human sovereignty, immutable records,
and current named output vocabulary. No optimizer behavior was evaluated.

### Coverage notes

WP1 and the corpus register call several current artifacts
`PORTFOLIO_INTELLIGENCE`; no alias decision is inferred.

## M34-C-0056 - Trust and evaluation semantic authority documents

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `AI_EVALUATION`
- Parent corpus id: `M34-C-0049`
- Work package discovered: `M34-WP5`
- Path anchor or pattern: `docs/architecture/platform_architecture.md::6.7 Trust & Evaluation; docs/investment/OPTIMIZER_PHILOSOPHY.md::AI Evaluation; docs/investment/EXECUTION_INTELLIGENCE_UX.md; docs/implementation/AI_EVALUATION_IMPLEMENTATION_PLAN.md`
- Scope granularity: `document set`
- Inclusion basis: Grade, calibration, counterfactual, human/AI, shadow, opportunity-cost, attribution-explanation, and trust-report authority
- Exclusion boundary: Evaluation calculation correctness, UX redesign, execution adoption, and runtime behavior
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Review ids: `M34-R-0012`, `M34-R-0014`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0045`, `M34-E-0046`
- Finding ids: `NONE`

### Scope statement

These artifacts define the observer-plane concepts and their read-only
relationship to Decision, Ledger, Market, and Portfolio sources.

### Search and traversal bounds

Three lenses, three portfolios, grade/counterfactual/calibration vocabulary,
as-of/failure rules, and immutable/read-only constraints only.

### Coverage notes

WP1 `AI_EVALUATION` is preserved as an audit classification; its mapping to
the reserved `Trust & Evaluation` domain requires ARB confirmation.

## M34-C-0057 - Closed execution and approval authority boundaries

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `GOVERNANCE`
- Parent corpus id: `M34-C-0049`
- Work package discovered: `M34-WP5`
- Path anchor or pattern: `docs/implementation/M32_EPIC_CLOSEOUT.md; docs/implementation/M33_11_supabase_auth_security_state_and_assurance_proof_of_concept.md; corresponding M32/M33 Decision Log entries`
- Scope granularity: `decision sections`
- Inclusion basis: WP1 section 1.3 and stop conditions; prevent observable legacy execution/decision terms from gaining stopped authority
- Exclusion boundary: Reopening M32/M33, provider investigation, identity design, and runtime adoption
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Review ids: `M34-R-0012`, `M34-R-0014`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0046`
- Finding ids: `NONE`

### Scope statement

The artifacts are read only to preserve canonical execution-planning NO-GO
and `STOP_M33_RUNTIME` while classifying current product vocabulary.

### Search and traversal bounds

Final readiness, active-versus-shadow path, terminal effects, and non-adoption
statements only.

### Coverage notes

No pure foundation or legacy runtime is proposed for adoption.

## M34-C-0058 - WP5 semantic-authority reconciliation report

- Record kind: `ARTIFACT`
- Status: `VERIFIED_IN_SCOPE`
- Domain: `GOVERNANCE`
- Parent corpus id: `M34-C-0049`
- Work package discovered: `M34-WP5`
- Path anchor or pattern: `docs/implementation/m34/audit/reports/M34_WP5_semantic_authority_matrix.md`
- Scope granularity: `report`
- Inclusion basis: WP5 required matrix, conflict, terminology, dependency, unknown, completeness, and handoff outputs
- Exclusion boundary: Finding classification, ownership disposition, redesign, calculation evaluation, and implementation
- Discovered by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Verified by / UTC: Lead Technical Auditor / 2026-07-19T08:38:31Z
- Review ids: `M34-R-0013`, `M34-R-0014`, `M34-R-0015`
- Child corpus ids: `NONE`
- Evidence ids: `M34-E-0048`, `M34-E-0049`, `M34-E-0050`
- Finding ids: `NONE`

### Scope statement

The report reconciles all frozen observable claims against the highest
available semantic authority without choosing unresolved owners.

### Search and traversal bounds

Forty semantic claim families, the registered authority corpus, exact Glossary
coverage, cross-domain dependencies, M32/M33 stop boundaries, and WP1 stop
conditions.

### Coverage notes

The report is complete; its recommendation returns affected dependent work to
the Architecture Review Board and does not authorize WP6.
