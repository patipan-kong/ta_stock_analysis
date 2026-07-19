# M34-WP2 - Product Evidence Baseline

**Date:** 2026-07-17

**Status:** Complete. Repository product-evidence collection only. No finding,
design, Portfolio Home proposal, implementation plan, or runtime change.

**Recommendation:** **Product case uncertain.**

## 1. Boundary and method

WP2 asks whether the repository contains evidence of a real product problem.
It does not ask whether the current calculations are correct or how a future
experience should work.

Every substantive claim below uses one of these labels:

| Claim class | Meaning in WP2 | Evidence treatment |
| --- | --- | --- |
| `Observed` | Directly present in inspected repository source at the audited revision | Registered as WP1 `DIRECT` evidence |
| `Documented` | Explicitly stated by current repository documentation | Registered as WP1 `DOCUMENTATION` evidence |
| `Measured` | Reproducible count or bounded search result over a stated repository corpus | Registered as `DIRECT` or `DERIVED` evidence with method and limits |
| `Inferred` | Interpretation that extends beyond what was directly observed, documented, or measured | Not promoted into the Evidence Register |
| `Unknown` | Repository evidence is absent, inaccessible, ambiguous, or insufficient | Not treated as favorable or unfavorable evidence |

The source revision is
`531b01b17a34955a65dd45f5e9386763652938ab`. No browser, production data,
external analytics, support system, interview archive, or runtime environment
was inspected. The only measured absence claims are the bounded searches in
`M34-E-0015` and `M34-E-0016`.

## 2. Current user journeys

These are repository-supported navigation paths, not measured histories of
what a person actually did.

| Journey | Current path | Claim class | Evidence |
| --- | --- | --- | --- |
| Authentication to the initial portfolio-related surface | Successful login routes to `/`; the root Dashboard loads all portfolios into a heatmap; a tile opens `/stock/[symbol]` | `Observed` | `M34-E-0001`, `M34-E-0005` |
| Enter and maintain one selected portfolio | Global Portfolio link opens `/portfolio`; the navbar or page selector selects the active portfolio; the page exposes portfolio creation/deletion, transaction/import controls, current holdings/cash/allocation, analysis, and price refresh | `Observed` | `M34-E-0002`, `M34-E-0003`, `M34-E-0006` |
| Move among overview, returns, and deeper quantitative analysis | Portfolio tabs link `/portfolio` → `/performance` → `/analytics`; all three consume the shared active portfolio | `Observed` | `M34-E-0003`, `M34-E-0004`, `M34-E-0007`, `M34-E-0008` |
| Investigate portfolio factors | `/portfolio` links to `/portfolio/[id]/factors`; the factor page retains Portfolio tabs and links back to `/portfolio` | `Observed` | `M34-E-0009` |
| Investigate an individual holding | Portfolio holdings and the root heatmap link to `/stock/[symbol]`; stock detail provides back navigation | `Observed` | `M34-E-0005`, `M34-E-0009` |
| Ask why a return occurred | `/performance` links “Why this return? See Attribution” to `/ai-analytics/attribution` | `Observed` | `M34-E-0007` |
| Investigate decision history and AI/human outcomes | `/operations-center` links to `/portfolio-intelligence`; that route uses the active portfolio and links back to Operations Center | `Observed` | `M34-E-0010` |
| Understand the intended navigation model | The System Guide describes Portfolio as one center with three sub-tabs and documents Portfolio Intelligence under the AI Operations Center | `Documented` | `M34-E-0011` |

`Unknown`: The repository does not establish which journey is most frequent,
whether the sequence matches actual user intent, where users abandon or
backtrack, or whether any path causes task failure.

## 3. Current portfolio entry points

| Entry point | Destination or state effect | Context | Claim class | Evidence |
| --- | --- | --- | --- | --- |
| Successful login | `/` | Initial authenticated destination | `Observed` | `M34-E-0001` |
| Navbar brand “Portfolio Intelligence” | `/` | Global legacy-dashboard entry | `Observed` | `M34-E-0002` |
| Main navigation “Portfolio” | `/portfolio` | Global primary entry; active match also covers performance, analytics, and stock routes | `Observed` | `M34-E-0002` |
| Navbar portfolio selector | Changes shared `activeId` without changing route | Global context entry | `Observed` | `M34-E-0002`, `M34-E-0003` |
| Portfolio tabs | `/portfolio`, `/performance`, `/analytics` | Secondary navigation inside the Portfolio grouping | `Observed` | `M34-E-0004` |
| Portfolio overview “DNA Analysis” | `/portfolio/[id]/factors` | Portfolio drill-down | `Observed` | `M34-E-0009` |
| Portfolio holding symbol or root heatmap tile | `/stock/[symbol]` | Instrument drill-down | `Observed` | `M34-E-0005`, `M34-E-0009` |
| Operations Center “Portfolio Intelligence” | `/portfolio-intelligence` | AI/decision investigation entry | `Observed` | `M34-E-0010` |
| Performance “Why this return?” | `/ai-analytics/attribution` | Cross-link into AI Evaluation | `Observed` | `M34-E-0007` |

`Measured`: The current main-navigation array has five entries; the Portfolio
secondary-navigation array has three destinations; four page files render
`PortfolioTabs`; and 18 page files call `usePortfolio()` (`M34-E-0014`).

## 4. Current navigation map

The map below is a `Measured` projection of explicit redirects and links in
`M34-E-0001` through `M34-E-0010`. It is not a proposed information
architecture.

```text
/login
  -> /
      Dashboard: cross-portfolio heatmap
      -> /stock/[symbol]

Global Navbar
  brand -> /
  Portfolio -> /portfolio
    shared active-portfolio selector
    Portfolio tabs
      -> /portfolio
          -> /portfolio/[id]/factors
          -> /stock/[symbol]
      -> /performance
          -> /ai-analytics/attribution
      -> /analytics
  AI Operations -> /operations-center
      -> /portfolio-intelligence
          -> back to /operations-center
```

`Observed`: Navbar active-state matching presents `/portfolio`,
`/performance`, `/analytics`, and `/stock` as members of the Portfolio
destination. It presents `/portfolio-intelligence` as a member of the AI
Operations destination (`M34-E-0002`).

`Unknown`: Static links do not establish visibility, comprehension, route
frequency, browser-history behavior, or successful task completion.

## 5. Current user jobs

The table records tasks the current repository exposes or explicitly
documents. It does not claim validated demand, priority, or frequency.

| Repository-supported task | Current surface(s) | Claim class | Evidence |
| --- | --- | --- | --- |
| Select, create, or delete a portfolio | Navbar selector; `/portfolio` | `Observed` | `M34-E-0002`, `M34-E-0003`, `M34-E-0006` |
| Establish or update portfolio facts through buy, sell, deposit, withdraw, dividend, and existing-position import controls | `/portfolio` | `Observed` | `M34-E-0006` |
| Inspect holdings, cash, current portfolio allocation, and sector allocation | `/portfolio` | `Observed` | `M34-E-0006` |
| Refresh prices and analyze portfolio holdings | `/portfolio` | `Observed` | `M34-E-0006` |
| Inspect cross-portfolio symbol exposure and move to stock investigation | `/`; `/stock/[symbol]` | `Observed` | `M34-E-0005`, `M34-E-0009` |
| Review portfolio value, P/L, investment return, snapshot history, equity curve, and benchmark comparison | `/performance` | `Observed` | `M34-E-0007` |
| Investigate quantitative KPIs, monthly returns, benchmarks, drawdown, equity curve, signals, and allocation analytics | `/analytics` | `Observed` | `M34-E-0008` |
| Investigate factor DNA for one portfolio | `/portfolio/[id]/factors` | `Observed` | `M34-E-0009` |
| Investigate why a return occurred through attribution | `/performance` → `/ai-analytics/attribution` | `Observed` | `M34-E-0007` |
| Review shadow performance, human-vs-AI comparison, regret, calibration, regime performance, and decision history | `/portfolio-intelligence` | `Observed` | `M34-E-0010` |
| Treat Overview, Returns, and Deep Analytics as the three documented parts of the Portfolio center | System Guide | `Documented` | `M34-E-0011` |
| Treat a portfolio as one strategy/accounting boundary and reserve whole-financial-picture aggregation for Wealth | Portfolio domain model | `Documented` | `M34-E-0013` |

`Unknown`: No repository evidence establishes which of these exposed tasks are
actual user jobs, which are incidental administrative capabilities, how often
they occur, or which outcomes users consider valuable.

## 6. Evidence supporting fragmentation

“Supporting” means consistent with the hypothesis. It does not prove user
harm.

| Claim | Class | Evidence | Evidentiary limit |
| --- | --- | --- | --- |
| Explicit links in the inspected journeys reach nine portfolio-relevant destinations across the root dashboard, Portfolio grouping, drill-down routes, AI Operations, and AI Evaluation | `Measured` | `M34-E-0014` | Route count does not measure confusion or unnecessary fragmentation |
| The first post-login surface is the root cross-portfolio Dashboard, while the main Portfolio entry opens a selected-portfolio overview | `Observed` | `M34-E-0001`, `M34-E-0005`, `M34-E-0006` | Distinct scopes may be useful; user expectation is unknown |
| Portfolio factor analysis is a dynamic drill-down and return attribution is in the AI Evaluation route tree rather than one of the three Portfolio tabs | `Observed` | `M34-E-0007`, `M34-E-0009` | Cross-domain placement may represent correct separation |
| Portfolio Intelligence is reached and parented through AI Operations rather than Portfolio secondary navigation | `Observed` | `M34-E-0002`, `M34-E-0010` | Current documentation presents this as intentional |
| Current portfolio, performance, analytics, factor, stock, and intelligence pages expose substantially different task sets | `Observed` | `M34-E-0005` through `M34-E-0010` | Different tasks do not necessarily require one surface |
| The roadmap declares a broad set of portfolio, analytics, execution-intelligence, and evaluation capabilities | `Documented` | `M34-E-0012` | Capability breadth does not establish a product-coherence problem |

`Inferred` and therefore not evidence: Users may experience the distinction
among the legacy Dashboard, Portfolio center, Portfolio Intelligence, and AI
Evaluation attribution as fragmentation.

## 7. Evidence against fragmentation

| Claim | Class | Evidence | Evidentiary limit |
| --- | --- | --- | --- |
| Global navigation exposes one Portfolio destination and treats overview, performance, analytics, and stock-detail prefixes as members of it | `Observed` | `M34-E-0002` | Active highlighting does not prove mental-model coherence |
| One three-destination Portfolio tab component is present on overview, performance, analytics, and factor pages | `Observed`, `Measured` | `M34-E-0004`, `M34-E-0014` | The factor destination itself is not one of the three tabs |
| One shared portfolio provider supplies selected-portfolio context across many routes | `Observed`, `Measured` | `M34-E-0003`, `M34-E-0014` | Shared state does not by itself create a coherent journey |
| The System Guide explicitly describes Portfolio as one center divided into Overview, Returns, and Deep Analytics | `Documented` | `M34-E-0011` | Intended grouping does not prove users understand it |
| Factor, stock-detail, Portfolio Intelligence, and attribution journeys have explicit inbound or return links | `Observed` | `M34-E-0007`, `M34-E-0009`, `M34-E-0010` | Link existence does not establish discoverability or successful return |
| The System Guide describes Portfolio Intelligence as decision memory reached from AI Operations, providing a stated reason for its separate parent | `Documented` | `M34-E-0011` | The reason has not been validated with users |
| Domain documentation distinguishes portfolio-scoped truth, cross-portfolio Wealth aggregation, Portfolio Intelligence meaning, and Experience presentation | `Documented` | `M34-E-0013` | Domain correctness does not settle current product usability |

`Inferred` and therefore not evidence: The current soft-consolidation structure
may already be sufficient for the product's actual users.

## 8. Unknowns requiring later verification

| Unknown | Why repository evidence is insufficient | Evidence required to resolve it |
| --- | --- | --- |
| Who the current users are and how many independently use the product | Source and roadmap do not establish an active user population | Bounded, non-personal user/role evidence or approved research record |
| Which portfolio task is performed most frequently | No product-behavior instrumentation was found in the bounded frontend search | Observed route/task-frequency evidence |
| Whether users recognize `/`, `/portfolio`, and `/portfolio-intelligence` as different scopes | Labels and docs show intended distinctions, not user comprehension | Direct usability or interview evidence |
| Whether users fail to find performance, analytics, factor, stock, attribution, or decision-history tasks | Links exist, but no failure, search, backtracking, or abandonment record was found | Task-completion and navigation-path evidence |
| Whether Portfolio tabs solved a prior navigation problem | Source comments call them soft consolidation, but no before/after product measure was found | Bounded before/after observation or documented research |
| Whether post-login `/` is useful, redundant, or surprising | The route is observed; user expectation and outcome are not | Landing-task and subsequent-path evidence |
| Whether separation of Portfolio Intelligence under AI Operations matches user intent | The repository documents that separation but does not validate it | User-language and task-grouping evidence |
| Whether desktop and mobile journeys are equally usable | Both render from shared arrays, but no interactive or accessibility evidence was collected | Device-specific task evidence |
| Whether external analytics, support, interviews, or unpublished research exist | Repository searches cannot inspect external systems or conversations | Produced, governed external evidence assessed under WP1 |
| Whether the exposed capabilities are correct and trustworthy | WP2 intentionally did not audit semantics, calculations, time, ownership, or degraded states | Later M34 semantic and read-contract work packages |

The required evidence descriptions identify proof gaps. They do not authorize
instrumentation, redesign, or implementation.

## 9. Initial product problem statement

`Observed`: Portfolio-related tasks currently span a legacy cross-portfolio
landing dashboard, a three-route selected-portfolio hub, portfolio/stock
drill-downs, and separately parented AI Operations and AI Evaluation routes.

`Observed` and `Documented`: The repository also contains deliberate
consolidation: one global Portfolio destination, shared active-portfolio state,
one three-tab Portfolio component, explicit cross-links/breadcrumbs, and a
System Guide that describes the intended grouping.

`Measured`: No product-analytics instrumentation or repository user-research
artifact was found within the bounded searches recorded by `M34-E-0015` and
`M34-E-0016`.

`Unknown`: Whether the current topology causes users to misunderstand scope,
fail tasks, lose trust, duplicate effort, or abandon investigation.

`Inferred`, not evidence: The defensible initial product problem is **an
unverified portfolio-coherence hypothesis**, not demonstrated fragmentation.
The repository shows structural distribution and structural consolidation but
does not establish the user consequence needed to call either one the real
product problem.

## 10. Confidence assessment

| Assessment area | Confidence | Basis |
| --- | --- | --- |
| Current route and entry-point map | High | Direct source links, redirects, navigation arrays, and bounded counts |
| Current repository-exposed tasks | High | Direct page controls, headings, and sections |
| Intended portfolio grouping | High | System Guide plus matching navigation/component structure |
| Capability breadth | Medium-high | Roadmap documentation, not runtime adoption evidence |
| Actual journey frequency and sequence | Very low | No repository behavior evidence found |
| User comprehension or navigation difficulty | Very low | No research, usability, or task evidence found |
| Fragmentation as a real product problem | Low | Structural evidence is mixed and user consequence is unknown |
| Confidence that the product case is presently uncertain | High | Neither support nor rejection satisfies an evidence threshold |

The overall WP2 conclusion is high-confidence about repository structure and
low-confidence about user need. That combination supports uncertainty, not a
positive or negative product verdict.

## 11. Recommendation

**Recommendation: Product case uncertain.**

- `Observed`: Portfolio capabilities are distributed across multiple route
  contexts.
- `Observed` and `Documented`: Existing navigation already consolidates the
  core Portfolio routes and intentionally separates some investigation tasks.
- `Measured`: The audited repository boundary contains no product-behavior or
  user-research evidence capable of deciding whether that structure causes a
  real problem.
- `Unknown`: External evidence may exist but was not available to this audit.

“Product case supported” is rejected for WP2 because structural distribution
without demonstrated user consequence is insufficient. “Product case
rejected” is also rejected because the repository does not prove that current
consolidation meets user needs. No Portfolio Home proposal follows from this
recommendation.

## 12. Register impact

- Corpus records added: `M34-C-0001` through `M34-C-0021`.
- Evidence records added and verified: `M34-E-0001` through `M34-E-0016`.
- Review events added: `M34-R-0001` through `M34-R-0004`.
- Findings created: zero.
- Decisions approved: zero. The WP2 recommendation is not an Architecture
  Review Board decision or M34 exit decision.
- Runtime or test evidence collected: zero.

## 13. Explicit non-adoption statement

M34-WP2 does not:

- redesign navigation, Portfolio, Portfolio Intelligence, AI Evaluation, or
  any user journey;
- propose Portfolio Home, a UI, route move, consolidation, or removal;
- assess semantic correctness, calculations, terminology, freshness,
  ownership, degraded states, or trustworthiness;
- add product analytics, telemetry, user research, tests, or runtime probes;
- modify frontend, backend, database, API, configuration, or runtime behavior;
- create a finding, approve a disposition, change the roadmap, or update the
  Decision Log;
- begin M34-WP3 or any later work package;
- authorize M34.1; or
- reopen M32 or M33.

M34.1 remains NO-GO.
