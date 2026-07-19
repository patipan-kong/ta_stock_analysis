# M34-WP3 - Surface and User-Question Inventory

**Date:** 2026-07-19

**Status:** Complete. Route-level portfolio surface inventory only. No
correctness judgment, calculation inspection, redesign, implementation plan,
finding, disposition, or runtime change.

**Recommendation:** **The inventory is complete enough for M34-WP5.** This
means WP5 has a bounded set of surfaces and claimed outputs to audit. It does
not mean any output is correct, trustworthy, well owned, or product-ready.

## 1. Boundary and method

WP3 inventories what each current surface claims to do. It does not validate
the claim. The audited repository revision is
`531b01b17a34955a65dd45f5e9386763652938ab`.

The inventory unit is a route-level `page.tsx` surface. A modal, card, table,
chart, shared tab bar, or responsive rendering is attributed to its host route
unless it has an independent route. This prevents one composed page from being
counted as several product surfaces while retaining its dependencies and
output claims in the host record.

The bounded universe is every `frontend/app/**/page.tsx` file:

- 24 route pages enumerated;
- 22 included in the surface inventory;
- 2 explicitly excluded: `/login`, which establishes entry but answers no
  portfolio question, and `/ai-analytics/system`, which presents AI system
  telemetry without portfolio scope; and
- zero unaccounted route pages.

Inclusion is deliberately broader than the three Portfolio tabs. A route is
included when it presents a portfolio fact, uses or changes the active
portfolio, investigates a portfolio-linked claim, configures portfolio-facing
behavior, or explains how the portfolio product is organized. Inclusion does
not transfer claim ownership to Experience or M34.

The five canonical question codes are:

| Code | User question |
| --- | --- |
| `Q1` | What do I own? |
| `Q2` | What is it worth? |
| `Q3` | What changed? |
| `Q4` | Can I trust the displayed values? |
| `Q5` | Where should I investigate further? |

`P` in a matrix means the surface explicitly presents the question as a
primary task. `S` means it supplies a secondary answer or investigation path.
`-` means no repository-supported claim was classified. These are inventory
classifications, not validated user needs.

## 2. Surface inventory

“Owner candidate” identifies the domain whose current claim appears to be
rendered. It is not an ownership ruling. Experience remains the owner of route
composition, navigation, accessibility, and presentation only.

### 2.1 Portfolio and instrument surfaces

| Corpus / route | Primary purpose; secondary purpose | Questions | Owner candidate | Read/write; scope | Navigation parent | Input dependencies and linked contracts | Output claims | Evidence | Unknowns |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `M34-C-0008` `/` | Cross-portfolio heatmap; stock drill-down | `Q1`, `Q2`, `Q3`, `Q5` | Portfolio + Market Data claims | `READ`; `CROSS_PORTFOLIO` | Login destination and navbar brand | portfolio list; `getHoldings`; `getPortfolioPrices` | Combined symbol exposure, market-value-sized tiles, price change, portfolio membership | `M34-E-0001`, `M34-E-0005`, `M34-E-0022` | `U01`, `U03`, `U10` |
| `M34-C-0009` `/portfolio` | Maintain and inspect one portfolio; factor and stock drill-down | `Q1`-`Q5` | Portfolio, Ledger, Market Data, and analysis claims | `MIXED`; `PORTFOLIO_SCOPED` | Global Portfolio → Overview tab | active portfolio; portfolio/holding/price/sector reads; portfolio, transaction, holding, analysis, and swap-permission writes | Holdings, cash, cost/value/P&L summaries, price change, allocation, sector allocation, signals, freshness labels | `M34-E-0002`, `M34-E-0003`, `M34-E-0004`, `M34-E-0006`, `M34-E-0022` | `U02`, `U03`, `U10`, `U11` |
| `M34-C-0010` `/performance` | Present value and return history; benchmark and attribution investigation | `Q2`, `Q3`, `Q4`, `Q5` | Portfolio + Analytics claims | `MIXED`; `PORTFOLIO_SCOPED` | Global Portfolio → Returns tab | active portfolio; snapshots; performance comparison; snapshot-generation and benchmark-backfill commands | Portfolio value, realized/unrealized P/L, investment return, non-performance events, return breakdown, curves, benchmarks, sector history, snapshot history | `M34-E-0004`, `M34-E-0007`, `M34-E-0022` | `U02`, `U10`, `U12` |
| `M34-C-0011` `/analytics` | Quantitative portfolio analysis; benchmark, signal, and allocation investigation | `Q3`, `Q4`, `Q5` | Analytics claims | `MIXED`; `PORTFOLIO_SCOPED` | Global Portfolio → Deep Analytics tab | active portfolio; performance-stats and comparison reads; benchmark-backfill command; client transformers | portfolio KPIs, monthly returns, benchmark comparison, drawdown, equity curve, signals, sector contribution, position P/L, cash utilization | `M34-E-0004`, `M34-E-0008`, `M34-E-0022` | `U02`, `U06`, `U10`, `U12` |
| `M34-C-0012` `/portfolio/[id]/factors` | Explain portfolio factor exposure; show sector concentration, drift, and per-stock scores | `Q1`, `Q5` | Analytics claims | `READ`; `PORTFOLIO_SCOPED_BY_ROUTE` | Portfolio overview drill-down; Portfolio tabs retained | route portfolio id; `getFactorExposure` | Portfolio DNA, factor exposure, sector concentration, drift insight, per-stock factor scores | `M34-E-0009`, `M34-E-0022` | `U04`, `U05`, `U10` |
| `M34-C-0015` `/stock/[symbol]` | Investigate one instrument; request or inspect analysis history and second opinions | `Q3`, `Q4`, `Q5` | Market Data plus unresolved stock/AI-analysis claim ownership | `MIXED`; `INSTRUMENT_SCOPED` | Portfolio group by navbar match; linked from dashboard, holdings, and watchlist | route symbol; stock quick read; analysis/history reads; analysis/opinion commands; history deletion | current analysis summary, price chart, technical/fundamental/news sections, sources, timestamps, history, second opinion | `M34-E-0009`, `M34-E-0022` | `U05`, `U10`, `U11` |

### 2.2 AI Operations and portfolio-intelligence surfaces

| Corpus / route | Primary purpose; secondary purpose | Questions | Owner candidate | Read/write; scope | Navigation parent | Input dependencies and linked contracts | Output claims | Evidence | Unknowns |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `M34-C-0034` `/operations-center` | Present current portfolio/AI operational status and run analysis; link advanced investigations | `Q4`, `Q5` | Portfolio Intelligence + source-domain claims | `MIXED`; `PORTFOLIO_SCOPED` | Global AI Operations | active portfolio; operations-status and trust-report reads; optimizer command; local display mode | portfolio summary, goal, market context, committee status, policy, station health, trust report, action-required state | `M34-E-0010`, `M34-E-0019`, `M34-E-0022` | `U02`, `U06`, `U07`, `U10` |
| `M34-C-0013` `/portfolio-intelligence` | Investigate human/AI decision outcomes; inspect decision memory | `Q3`, `Q4`, `Q5` | Portfolio Intelligence, Analytics, and AI Evaluation claims | `READ`; `PORTFOLIO_SCOPED` | AI Operations → Portfolio Intelligence | active portfolio; AI-vs-human, attribution, calibration, regime, decision-memory, and shadow reads | human/AI comparison, regret, confidence calibration, regime performance, decision timeline, shadow portfolio | `M34-E-0010`, `M34-E-0022` | `U02`, `U06`, `U07`, `U10` |
| `M34-C-0035` `/optimizer` | Run and inspect portfolio analysis/recommendations; record legacy decision labels | `Q4`, `Q5` | Optimizer / Portfolio Intelligence claims | `MIXED`; `PORTFOLIO_SCOPED` | AI Operations → Optimizer | active portfolio; optimizer run/history; strategy/persona; operations status; decision-memory/shadow reads; persona and legacy decision writes | analysis, AI recommendation, displayed execution-plan projection, warnings, history, persona/policy, decision labels | `M34-E-0019`, `M34-E-0022` | `U06`, `U07`, `U10`, `U11` |
| `M34-C-0036` `/goal-wizard` | Capture a goal profile for the active portfolio; summarize the entered profile | none directly | Goal-profile owner candidate within Portfolio Intelligence | `WRITE`; `PORTFOLIO_SCOPED` | AI Operations → Goal Profile | active portfolio; `updateGoalProfile` | goal type, target amount/date, priority, risk personality, saved summary | `M34-E-0019`, `M34-E-0022` | `U02`, `U08`, `U10` |

### 2.3 AI Evaluation surfaces

All nine routes use the selected portfolio through `PortfolioContext` and are
composed under the AI Evaluation hub. Their current page comments state that
the displayed backend results are rendered without introducing a new metric;
WP3 records that claim but does not verify it.

| Corpus / route | Primary purpose; secondary purpose | Questions | Owner candidate | Read/write; scope | Navigation parent | Input dependencies and linked contracts | Output claims | Evidence | Unknowns |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `M34-C-0025` `/ai-analytics` | Summarize AI evaluation; link detailed lenses | `Q3`, `Q4`, `Q5` | AI Evaluation | `READ`; `PORTFOLIO_SCOPED` | Global AI Evaluation → Scorecard | active portfolio, period; `getEvaluationScorecard` | belief, execution, and outcome grades; recent grades; three-portfolio summary | `M34-E-0018`, `M34-E-0020`, `M34-E-0022` | `U06`, `U10`, `U12` |
| `M34-C-0026` `/ai-analytics/recommendations` | List recommendation records; filter and open one report | `Q3`, `Q5` | AI Evaluation | `READ`; `PORTFOLIO_SCOPED` | AI Evaluation → Recommendations | active portfolio, paging/filter state; `getRecommendationsLedger` | recommendation ledger, decision/consensus classifications, horizons, counterfactual values | `M34-E-0018`, `M34-E-0020`, `M34-E-0022` | `U07`, `U10` |
| `M34-C-0027` `/ai-analytics/recommendations/[id]` | Explain one recommendation from plan through outcome | `Q3`, `Q4`, `Q5` | AI Evaluation | `READ`; `PORTFOLIO_AND_RECORD_SCOPED` | Recommendations ledger | active portfolio, route snapshot id; `getRecommendationReportCard` | immutable-plan section, what-happened section, frozen-shadow-versus-benchmark outcome | `M34-E-0018`, `M34-E-0020`, `M34-E-0022` | `U07`, `U10` |
| `M34-C-0028` `/ai-analytics/execution` | List and segment recorded decision outcomes; open decision detail | `Q3`, `Q4`, `Q5` | AI Evaluation | `READ`; `PORTFOLIO_SCOPED` | AI Evaluation → Decisions | active portfolio, period; `getExecutionLedger` | decision ledger, class-segmented acceptance, counterfactual values | `M34-E-0018`, `M34-E-0020`, `M34-E-0022` | `U07`, `U10` |
| `M34-C-0029` `/ai-analytics/execution/[id]` | Explain one recorded decision's plan-versus-actual data | `Q3`, `Q4`, `Q5` | AI Evaluation | `READ`; `PORTFOLIO_AND_RECORD_SCOPED` | Execution ledger | active portfolio, route decision id; `getExecutionDetail` | per-trade planned/actual fields, deltas, partial-execution warning, as-of state | `M34-E-0018`, `M34-E-0020`, `M34-E-0022` | `U07`, `U10` |
| `M34-C-0030` `/ai-analytics/human-vs-ai` | Compare human and AI decision outcomes; link opportunity-cost detail | `Q3`, `Q5` | AI Evaluation | `READ`; `PORTFOLIO_SCOPED` | AI Evaluation → Human vs AI | active portfolio, period; `getHumanVsAiScoreboard` | scoreboard, net effect, trade-class and override-type segments | `M34-E-0018`, `M34-E-0020`, `M34-E-0022` | `U06`, `U07`, `U10` |
| `M34-C-0031` `/ai-analytics/opportunity-cost` | Explain counterfactual cost of divergence; identify system deferrals | `Q3`, `Q4`, `Q5` | AI Evaluation | `READ`; `PORTFOLIO_SCOPED` | Human vs AI drill-down | active portfolio, period; `getOpportunityCost` | net counterfactual value, waterfall, divergence rows, deferrals | `M34-E-0018`, `M34-E-0020`, `M34-E-0022` | `U06`, `U07`, `U10` |
| `M34-C-0032` `/ai-analytics/portfolios` | Compare Ideal, AI, and user portfolio series; explain two gaps and risk | `Q2`, `Q3`, `Q4`, `Q5` | AI Evaluation + Analytics claims | `READ`; `PORTFOLIO_SCOPED` | AI Evaluation → Portfolio Comparison | active portfolio, period; `getShadowPerformanceSummary` | three indexed portfolios, implementation and human-deviation gaps, risk table | `M34-E-0018`, `M34-E-0020`, `M34-E-0022` | `U06`, `U07`, `U10`, `U12` |
| `M34-C-0033` `/ai-analytics/attribution` | Explain sources of return; switch among sector, regime, and holding views | `Q3`, `Q4`, `Q5` | Analytics + AI Evaluation presentation | `READ`; `PORTFOLIO_SCOPED` | AI Evaluation → Attribution; cross-linked from Performance | active portfolio, period/tab; `getAttributionSummary`; `getRegimeAttribution` | effect waterfall, residual/unexplained value, regime attribution, explicit unavailable states for unsupported views | `M34-E-0018`, `M34-E-0020`, `M34-E-0022` | `U06`, `U10`, `U12` |

### 2.4 Adjacent, administrative, and explanatory surfaces

| Corpus / route | Primary purpose; secondary purpose | Questions | Owner candidate | Read/write; scope | Navigation parent | Input dependencies and linked contracts | Output claims | Evidence | Unknowns |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `M34-C-0037` `/watchlist` | Maintain and investigate an instrument watchlist; buy into the active portfolio | `Q1`, `Q5` | Watchlist/analysis claims; Ledger owns the portfolio transaction | `MIXED`; `CROSS_PORTFOLIO_READ_AND_PORTFOLIO_WRITE` | Global Watchlist | watchlist reads/writes; active portfolio only for `buyTransaction`; stock-detail links | symbols, sectors, signals, upside, risk, analysis freshness; selected-portfolio buy target | `M34-E-0021`, `M34-E-0022` | `U05`, `U09`, `U10`, `U11` |
| `M34-C-0038` `/settings` | Configure system analysis and optimizer behavior; maintain portfolio/sector limits | none directly | Configuration/governance owner candidate; affected claim owners remain separate | `MIXED`; `SYSTEM_WIDE` | Admin Settings | settings reads/patches; sector backfill command | provider/model/source settings, portfolio limits, sector allocation limits, data-management result | `M34-E-0021`, `M34-E-0022` | `U08`, `U10` |
| `M34-C-0018` `/system-guide` | Explain system concepts and navigation; describe portfolio and AI capabilities | `Q4`, `Q5` | Documentation + Experience presentation | `READ`; `SYSTEM_WIDE` | Global Guide | static repository content and local tab state | portfolio center map, stock-analysis sections, optimizer/strategy/factor/intelligence explanations, navigation shortcuts | `M34-E-0011` | `U08`, `U13` |

## 3. User Question Matrix

| Surface | `Q1` | `Q2` | `Q3` | `Q4` | `Q5` |
| --- | :---: | :---: | :---: | :---: | :---: |
| `/` | `P` | `S` | `S` | `-` | `S` |
| `/portfolio` | `P` | `P` | `S` | `S` | `S` |
| `/performance` | `-` | `P` | `P` | `S` | `S` |
| `/analytics` | `-` | `-` | `P` | `S` | `P` |
| `/portfolio/[id]/factors` | `S` | `-` | `-` | `-` | `P` |
| `/stock/[symbol]` | `-` | `-` | `S` | `S` | `P` |
| `/operations-center` | `-` | `-` | `-` | `P` | `P` |
| `/portfolio-intelligence` | `-` | `-` | `P` | `S` | `P` |
| `/optimizer` | `-` | `-` | `-` | `S` | `P` |
| `/goal-wizard` | `-` | `-` | `-` | `-` | `-` |
| `/ai-analytics` | `-` | `-` | `S` | `P` | `P` |
| `/ai-analytics/recommendations` | `-` | `-` | `P` | `-` | `P` |
| `/ai-analytics/recommendations/[id]` | `-` | `-` | `P` | `S` | `P` |
| `/ai-analytics/execution` | `-` | `-` | `P` | `S` | `P` |
| `/ai-analytics/execution/[id]` | `-` | `-` | `P` | `S` | `P` |
| `/ai-analytics/human-vs-ai` | `-` | `-` | `P` | `-` | `P` |
| `/ai-analytics/opportunity-cost` | `-` | `-` | `P` | `S` | `P` |
| `/ai-analytics/portfolios` | `-` | `S` | `P` | `S` | `P` |
| `/ai-analytics/attribution` | `-` | `-` | `P` | `S` | `P` |
| `/watchlist` | `S` | `-` | `-` | `-` | `P` |
| `/settings` | `-` | `-` | `-` | `-` | `-` |
| `/system-guide` | `-` | `-` | `-` | `S` | `P` |

Evidence: `M34-E-0023`. The matrix classifies visible claims only. It does not
assert that a user accepts the wording, that the answer is complete, or that
the data supports it.

## 4. Read vs Write Matrix

| Mode | Surfaces | Transport/action basis |
| --- | --- | --- |
| `READ` | `/`, `/portfolio/[id]/factors`, `/portfolio-intelligence`, all nine AI Evaluation routes, `/system-guide` | Repository surfaces issue only reads for their primary data or render static content |
| `WRITE` | `/goal-wizard` | The route collects local input and persists a goal-profile update |
| `MIXED` | `/portfolio`, `/performance`, `/analytics`, `/stock/[symbol]`, `/operations-center`, `/optimizer`, `/watchlist`, `/settings` | Each route combines reads with at least one POST, PUT, PATCH, or DELETE contract or an explicit command action |

`READ` describes the inspected route contract, not the internal behavior of a
backend GET. No idempotency, persistence, or side-effect correctness was
audited. Evidence: `M34-E-0022`, `M34-E-0024`.

## 5. Portfolio Scope Matrix

| Scope class | Surfaces | Scope source |
| --- | --- | --- |
| `CROSS_PORTFOLIO` | `/` | Iterates the portfolio collection and combines holdings/prices by symbol |
| `PORTFOLIO_SCOPED` | `/portfolio`, `/performance`, `/analytics`, `/operations-center`, `/portfolio-intelligence`, `/optimizer`, `/goal-wizard`, all nine AI Evaluation routes | Shared active portfolio id |
| `PORTFOLIO_SCOPED_BY_ROUTE` | `/portfolio/[id]/factors` | Dynamic route portfolio id |
| `PORTFOLIO_AND_RECORD_SCOPED` | recommendation detail and execution detail | Shared active portfolio plus route record id |
| `INSTRUMENT_SCOPED` | `/stock/[symbol]` | Dynamic symbol; may be entered from several parents |
| `CROSS_PORTFOLIO_READ_AND_PORTFOLIO_WRITE` | `/watchlist` | Global watchlist reads; shared active portfolio selects the buy destination |
| `SYSTEM_WIDE` | `/settings`, `/system-guide` | No selected portfolio is required for the inspected content |

Evidence: `M34-E-0024`. Workspace tenancy, actor authorization, and database
scope correctness are outside WP3 and are not implied by this classification.

## 6. Navigation Ownership Map

```text
Authenticated shell / global Experience navigation
├─ brand -> /                                  [cross-portfolio dashboard]
├─ Portfolio -> /portfolio
│  ├─ Portfolio tabs -> /portfolio
│  ├─ Portfolio tabs -> /performance
│  │  └─ Why this return? -> /ai-analytics/attribution
│  ├─ Portfolio tabs -> /analytics
│  ├─ overview drill-down -> /portfolio/[id]/factors
│  └─ dashboard/holding links -> /stock/[symbol]
├─ Watchlist -> /watchlist
│  └─ symbol -> /stock/[symbol]
├─ AI Operations -> /operations-center
│  ├─ advanced analysis -> /optimizer
│  ├─ decision memory -> /portfolio-intelligence
│  └─ goal profile -> /goal-wizard
├─ AI Evaluation -> /ai-analytics
│  ├─ /ai-analytics/recommendations
│  │  └─ /ai-analytics/recommendations/[id]
│  ├─ /ai-analytics/execution
│  │  └─ /ai-analytics/execution/[id]
│  ├─ /ai-analytics/human-vs-ai
│  │  └─ /ai-analytics/opportunity-cost
│  ├─ /ai-analytics/portfolios
│  └─ /ai-analytics/attribution
├─ Guide -> /system-guide
└─ Admin -> /settings
```

Experience is the candidate owner of the navigation relationships only. The
parent does not acquire ownership of a child's data or semantics. Evidence:
`M34-E-0002`, `M34-E-0004`, `M34-E-0007`, `M34-E-0009`, `M34-E-0010`,
`M34-E-0018`, `M34-E-0025`.

## 7. Duplicate Surface Candidates

These are inventory overlaps for WP5 comparison. They are not findings and do
not imply that either surface should move, merge, or disappear.

| Candidate | Shared visible claim area | Observed distinction to preserve during later verification |
| --- | --- | --- |
| `/` and `/portfolio` | holdings/exposure, value, price change, stock drill-down | cross-portfolio symbol heatmap versus selected-portfolio maintenance and detail |
| `/portfolio` and `/operations-center` | portfolio overview/status | portfolio/ledger inspection versus AI-operational summary and action status |
| `/performance` and `/analytics` | return, benchmark, equity curve, portfolio analytics | snapshot/value history versus broader quantitative analysis and filters |
| `/performance` and `/ai-analytics/portfolios` | portfolio curves and comparative performance | benchmark/since-inception framing versus Ideal/AI/You counterfactual comparison |
| `/analytics` and `/portfolio/[id]/factors` | allocation, sector, style/risk investigation | general allocation analytics versus factor-DNA drill-down |
| `/portfolio-intelligence` and `/ai-analytics/human-vs-ai` | human-versus-AI outcome comparison | multi-panel decision memory versus bounded evaluation scoreboard |
| `/portfolio-intelligence` and `/ai-analytics/attribution` | attribution/regime explanations | broad intelligence dashboard versus dedicated return-attribution route |
| `/portfolio-intelligence` and `/ai-analytics` | calibration, outcomes, model/user comparison | legacy intelligence composition versus evaluation scorecard/lenses |
| `/optimizer` and `/ai-analytics/execution*` | “execution” and decision records | recommendation/legacy decision capture versus read-only outcome evaluation |
| `/optimizer` and `/ai-analytics/recommendations*` | recommendation records and report detail | analysis/action surface versus historical evaluation ledger/report card |

Evidence: `M34-E-0026`. No candidate is classified as a duplicate concept
until WP5 verifies semantic identity, source ownership, time basis, and
contract equivalence.

## 8. Candidate Semantic Boundaries

| Candidate boundary | Claims presently associated with it | Surfaces that consume or present it | Classification limit |
| --- | --- | --- | --- |
| Experience | route composition, navigation, labels, formatting, visible loading/error/empty states | all 22 | Owns presentation, not displayed truth |
| Portfolio | portfolio identity, selected scope, holdings interpretation, portfolio-level value composition | `/`, `/portfolio`, performance/analytics consumers | Candidate only; exact read contract is for WP5 |
| Ledger | transactions, cash movements, quantities, costs, realized events | `/portfolio`, `/watchlist` buy path, performance consumers | Write/result semantics not inspected |
| Market Data | prices, change, source observation time and availability | dashboard, portfolio, stock, downstream analytics | Freshness and fallback semantics not inspected |
| Analytics | return, benchmark, risk, factor, contribution, attribution, calibration inputs | performance, analytics, factors, intelligence, evaluation | Metric correctness and ownership conflicts not inspected |
| Portfolio Intelligence / Optimizer | recommendations, policies, goal/profile context, operational status, decision memory | Operations Center, Optimizer, Portfolio Intelligence | M32/M33 remain closed; no runtime adoption is implied |
| AI Evaluation | grading, counterfactual comparison, report cards, human/AI outcome explanation | nine AI Evaluation routes and linked intelligence panels | Source lineage and claim reuse require WP5 verification |
| Watchlist / stock analysis | candidate-instrument monitoring and instrument-level analysis | Watchlist and stock detail | Canonical owner is not established by WP3 |
| Documentation/configuration governance | stated navigation/model and system-wide analysis constraints | System Guide and Settings | Descriptions/settings do not become source-domain truth |

This table implements “one concept, one owner” by naming candidate boundaries
without appointing Experience or a composition surface as the owner. Evidence:
`M34-E-0013`, `M34-E-0026`.

## 9. Unknown Classifications

| ID | Unknown | Why WP3 cannot classify it |
| --- | --- | --- |
| `U01` | Whether a displayed route answers an actual prioritized user job | WP2 found no repository behavior or research evidence |
| `U02` | The final single owner for each mixed-purpose page region | A surface composes several claim types; WP3 does not make ownership rulings |
| `U03` | Ownership and canonical contract of client-presented portfolio summaries | WP3 records labels and inputs but does not inspect calculations or source authority |
| `U04` | Required relationship between factor-route portfolio id and shared active portfolio id | The two scope mechanisms are observed; their intended invariant is not stated by WP3 evidence |
| `U05` | Canonical owner of instrument-level AI/technical/fundamental analysis and Watchlist claim meaning | Current route and API names do not constitute governance authority |
| `U06` | Whether similarly named analytics/intelligence/evaluation outputs share one semantic contract | Requires field-, period-, time-, provenance-, and lineage-level verification |
| `U07` | How legacy “execution” and decision vocabulary should be interpreted after `STOP_M33_RUNTIME` | M32/M33 boundaries prohibit using inventory work to reopen or normalize runtime authority |
| `U08` | Final owner of goal profiles, portfolio limits, sector limits, and corresponding documentation | Configuration location does not establish business-rule ownership |
| `U09` | Exact boundary between global Watchlist state and the selected-portfolio transaction action | WP3 observes both scopes but does not audit write semantics |
| `U10` | Backend source lineage, time basis, optionality, degraded-state meaning, and calculation contract behind each frontend API type | WP3 follows only the route-to-client-contract boundary; WP5 must continue the trace |
| `U11` | Whether embedded modals/cards or responsive variants need independent semantic records | They are grouped under host routes for inventory; WP5 may split a claim when its contract differs |
| `U12` | Whether similarly titled outputs use the same period, benchmark, valuation basis, or as-of time | Naming and layout are insufficient evidence |
| `U13` | Whether explanatory documentation remains synchronized with every runtime surface | WP3 inventories the guidance claim but does not compare implementation semantics |
| `U14` | Whether runtime-only, externally hosted, or feature-flagged portfolio surfaces exist | Static repository inspection cannot prove absence outside the enumerated route corpus |

Unknowns are not findings and cannot support a readiness decision.

## 10. Inventory Completeness Assessment

| Completeness dimension | Result | Basis |
| --- | --- | --- |
| Route-page universe | Complete for audited revision | 24 of 24 `frontend/app/**/page.tsx` files accounted for |
| Included portfolio-facing surfaces | Complete at route level | 22 surfaces contain portfolio claims, dependencies, writes, configuration, or explanation |
| Explicit exclusions | Complete | `/login` and `/ai-analytics/system` have recorded scope reasons |
| Shared navigation parents | Complete for static routes | Navbar, Portfolio tabs, AI Evaluation tabs, breadcrumbs, and inspected route links mapped |
| Read/write classification | Complete at frontend contract level | Every included surface assigned `READ`, `WRITE`, or `MIXED` |
| Portfolio scope classification | Complete at frontend selection/route level | Every included surface assigned a scope class |
| Input/API links | Sufficient for WP5 entry | Imported client functions and HTTP method/path contracts are recorded |
| Output-claim labels | Sufficient for WP5 entry | Every surface has a bounded list of visible claims |
| Backend lineage and correctness | Intentionally incomplete | Deferred to semantic contract work; no calculation was inspected |
| Runtime surface behavior | Not collected | WP3 is static inventory only |
| Component-level semantic variants | Conditionally incomplete | Split only if WP5 proves a component has an independent semantic contract |

Evidence: `M34-E-0017`, `M34-E-0027`.

## 11. Recommendation for WP5

**Yes — the inventory is complete enough for WP5.**

WP5 can start from a closed route universe, named output claims, initial
question mappings, candidate owners, explicit input/API boundaries, and a
catalogue of overlap candidates and unknowns. The inventory does not require a
navigation or product redesign before semantic verification begins.

The recommendation has four conditions:

1. WP5 must treat owner entries as candidates, not decisions.
2. WP5 must trace each material output claim beyond `frontend/lib/api.ts` to
   its authoritative backend/domain contract and tests.
3. WP5 must not infer semantic identity from duplicate labels or shared API
   response shapes.
4. WP5 must preserve `STOP_M33_RUNTIME`; legacy execution/decision surfaces
   may be audited as existing claims but cannot be adopted or upgraded.

This recommendation does not authorize M34.1. M34.1 remains NO-GO.

## 12. Register Impact

- New corpus records: `M34-C-0022` through `M34-C-0039`.
- New verified evidence records: `M34-E-0017` through `M34-E-0027`.
- New verification events: `M34-R-0005` through `M34-R-0008`.
- Findings created: zero.
- Decisions approved: zero. The WP3 recommendation is a work-package
  readiness recommendation, not an Architecture Review Board decision.
- Runtime or test evidence collected: zero.

## 13. Explicit Non-Adoption Statement

M34-WP3 does not:

- inspect or judge a calculation, metric, formula, valuation, attribution,
  return, risk, factor, optimizer, or AI result;
- decide that two surfaces are duplicates;
- assign final domain ownership;
- redesign navigation, routes, Portfolio, AI Operations, AI Evaluation,
  Settings, Watchlist, or any user journey;
- propose Portfolio Home, UI changes, implementation work, migrations, or
  runtime changes;
- create a finding, disposition, Decision Log entry, or M34 exit decision;
- modify frontend, backend, database, API, tests, configuration, or runtime;
- authorize identity, approval, execution-intent, certificate, or other M33
  runtime work;
- reopen M32 or M33; or
- authorize M34.1.

M34.1 remains NO-GO.
