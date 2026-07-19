# M34-WP4 - Read Contract and Lineage Inventory

**Date:** 2026-07-19

**Status:** Complete. Static read-contract and observable-lineage inventory
only. No semantic judgment, calculation assessment, ownership ruling, finding,
decision, redesign, implementation, or runtime execution.

**Recommendation:** **The read-contract inventory is complete enough for
M34-WP5.** This means WP5 has a bounded, evidence-backed map from every WP3
material read claim to its current transport, handler, service, read model, and
observable source. It does not mean that any contract, formula, owner,
freshness rule, or displayed claim is correct.

## 1. Boundary and method

WP4 follows the 22 frozen WP3 surfaces without changing their inclusion,
purpose, question, scope, or owner-candidate classifications. The audited
repository revision is
`531b01b17a34955a65dd45f5e9386763652938ab`.

The inventory unit is one material response contract consumed by a WP3
surface. A contract is included when it supplies a visible output claim listed
in WP3 or supplies the selected-portfolio context required to issue that read.
Shared contracts are recorded once with every observed consumer. The current
population is:

- 43 HTTP `GET` response contracts;
- one static repository-content contract for `/system-guide`;
- zero unaccounted material WP3 read claims; and
- zero runtime observations.

The response from `GET /ai-models` is one of the 43 HTTP contracts even though
its primary source is the repository file `backend/ai-model.json` rather than a
database row.

WP4 does not relabel a command response as a read contract. POST/PATCH/PUT/
DELETE acknowledgements, optimizer live-run results, analysis-job progress
streams, and Decision Workspace analytical command results remain outside this
read-contract population. Their persisted or subsequently queried projections
are included when a WP3 surface reads them through a current `GET` contract.
`/goal-wizard` has no independent material read beyond the shared
`listPortfolios()` context. `/system-guide` has no frontend API call.

“Service entry” means the first backend function that owns or composes the
response path. It does not declare semantic ownership. “Primary read model” is
the immediate row projection, computed projection, configuration projection,
or in-memory projection returned to the handler. “Primary persistence source”
records only sources directly evidenced in the traced path; a missing or
external source remains explicit.

Lineage confidence is traceability confidence only:

| Level | Meaning |
| --- | --- |
| `HIGH` | Frontend call, route, handler/service, response shape, and primary source are explicit in repository source. |
| `MEDIUM` | The response boundary is explicit, but part of the source path uses provider calls, JSON payloads, dynamic helper imports, caches, or composite services whose complete runtime input is not statically closed. |
| `UNKNOWN` | A required hop is not established. Such a gap is recorded in section 10, never inferred. |

Evidence: `M34-E-0028` through `M34-E-0038`.

## 2. Read Contract Inventory

Backend handlers below return ordinary `dict` / `list[dict]` projections and
do not declare a named FastAPI `response_model` for these routes. “DTO” names
are the TypeScript consumer interfaces in `frontend/lib/api.ts`; they are
transport descriptions, not ownership or correctness claims.

### 2.1 Portfolio, market, instrument, and shared-scope contracts

| Originating surface(s) | Frontend call -> backend endpoint | Service entry / primary read model | Primary source | Transport objects / response DTO | Visible output claims | Known transformations / aggregations | Owner candidate | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Shared selected-portfolio context used by portfolio-scoped WP3 routes | `listPortfolios()` -> `GET /portfolios` | `main.list_portfolios`; ordered ORM-row projection | `portfolios` (`Portfolio`) | no request body; `Portfolio[]` | portfolio id/name, cash, goal target, created time used for selection | handler maps rows; `PortfolioContext` selects a saved valid id or the first row | Portfolio | `HIGH` |
| `/`, `/portfolio` | `getHoldings()` -> `GET /portfolios/{portfolio_id}/holdings` | `main.list_holdings`; enriched holding-row projection | `portfolio_items`, `analysis_cache`, `agent_cache`; latest consensus from `analysis_history` | path id; `PortfolioItem[]` | symbols, quantities, costs, sectors, analysis/signals, price placeholders | `_enrich_holdings`, cached-analysis join, fundamental-cache projection, latest-day consensus join | Portfolio + Ledger + analysis claim candidates | `HIGH` |
| `/`, `/portfolio` | `getPortfolioPrices()` -> `GET /portfolios/{portfolio_id}/prices` | `main.get_portfolio_prices` -> `data_fetcher.fetch_price_info`; quote projection | `portfolio_items`, `agent_cache`, `market_data_cache`; configured market provider when cache cannot serve | path id; `PriceRefreshItem[]` | current/previous price, change, observation label, upside | concurrent quote reads, fundamental target join, DR parent-price join, response shaping | Market Data plus analysis claim candidate | `MEDIUM` |
| `/portfolio` | `getSectorBreakdown()` -> `GET /portfolios/{portfolio_id}/sector-breakdown` | `main.get_sector_breakdown`; handler-built sector projection | `portfolio_items`, `settings` | path id; `SectorBreakdown` | sector values, weights, members, limits, status | groups holding rows by normalized sector and joins configured limits | Portfolio + configuration candidates | `HIGH` |
| `/watchlist` | `getWatchlist()` -> `GET /watchlist` | `main.list_watchlist`; enriched watchlist-row projection | `watchlist`, `analysis_cache`, `agent_cache`, `market_data_cache`, registry tables through `registry_lookup`; provider fallback | `WatchlistItem[]` | symbols, sectors, signals, upside, risk, analysis and price timestamps, registry state | cached-analysis join, quote join, DR mapping, registry projection, `_watchlist_row` shaping | Watchlist / instrument analysis + Market Data candidates | `MEDIUM` |
| `/stock/[symbol]` | `getStockQuick()` -> `GET /stocks/{symbol}` | `main.get_stock_quick` -> `_fetch_agents`; composed instrument projection | `agent_cache`, `analysis_cache`, `market_data_cache`; configured agents/providers | path symbol; `FullAnalysis` | technical/fundamental/news sections, cached summary, source list, analysis timestamp | symbol resolution, agent result composition, cached summary projection | Market Data + stock/AI-analysis candidates | `MEDIUM` |
| `/stock/[symbol]` | `getStockChart()` -> `GET /stocks/{symbol}/chart` | `main.get_stock_chart` -> `agents.chart_data.fetch_chart_data`; candle/indicator projection | `market_data_cache`; configured market provider fallback | symbol, period, interval; `ChartData` / `ChartCandle[]` | price chart and returned indicator series | symbol resolution, history-to-candle projection, chart-data transformations | Market Data + instrument-analysis candidates | `MEDIUM` |
| `/stock/[symbol]` | `getAnalysisHistory()` -> `GET /analysis/history/{symbol}` | `main.get_analysis_history`; ordered history-row projection | `analysis_history` | path symbol; `AnalysisHistoryItem[]` | prior analyses, signals, models, sources, timestamps | symbol resolution, newest-first limit, `_history_row` mapping | Stock/AI-analysis candidate | `HIGH` |
| `/stock/[symbol]` | `getConsensus()` -> `GET /analyze/{symbol}/consensus` | `main.get_consensus`; handler-built consensus projection | `analysis_history` | path symbol; `ConsensusResult` | dominant signal, agreement, disagreement flag, counts, breakdown | limits to the latest UTC calendar day and aggregates recent history rows | Stock/AI-analysis candidate | `HIGH` |
| `/settings`, `/stock/[symbol]` | `getAIModels()` -> `GET /ai-models` | `main.get_ai_models`; static JSON projection | `backend/ai-model.json` | `AIModelsConfig` | available provider/model configuration | JSON file load only | Configuration candidate | `HIGH` |
| `/settings`, `/stock/[symbol]` | `getAISettings()` -> `GET /settings/ai-models` | `main.get_ai_settings_endpoint` -> `_get_ai_settings`; settings projection with defaults | `settings` | `AISettings` | selected analysis and optimizer models/providers | workspace settings rows merged with defaults | Configuration candidate | `HIGH` |

Evidence: `M34-E-0028`, `M34-E-0029`, `M34-E-0030`, `M34-E-0035`.

### 2.2 Snapshot, performance, and analytical contracts

| Originating surface(s) | Frontend call -> backend endpoint | Service entry / primary read model | Primary source | Transport objects / response DTO | Visible output claims | Known transformations / aggregations | Owner candidate | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/performance` | `getSnapshots()` -> `GET /portfolios/{portfolio_id}/snapshots` | `main.list_snapshots`; ordered snapshot-row projection | `portfolio_snapshots` | path id, limit; `PortfolioSnapshotRow[]` | value, P/L, return, holdings/cash history and snapshot metadata | oldest-first query and `_snapshot_row` JSON projection | Portfolio + Analytics candidates | `HIGH` |
| `/performance`, `/analytics` | `getPerformanceComparison()` -> `GET /analytics/performance-comparison` | `main.get_performance_comparison`; handler-built comparison projection | `portfolio_snapshots`, `benchmark_prices`, `portfolios` | portfolio id, benchmark list; `PerformanceComparisonResult` | normalized portfolio/benchmark curves and series metadata | snapshot-series indexing, benchmark-series alignment, flat chart-row assembly | Analytics | `HIGH` |
| `/analytics` | `getPerformanceStats()` -> `GET /analytics/performance-stats` | `main.get_performance_stats` -> `analytics.quant_engine` builders; cached aggregate projection | `portfolio_snapshots`, `benchmark_prices`, `signal_history`; in-process analytics cache | portfolio id, benchmark and include flags; `PerformanceStatsResult` | portfolio KPIs, benchmark stats, signals, allocation analytics, optional curves | service builders aggregate snapshots/benchmarks/signals; optional chart projections; client display transformers | Analytics | `HIGH` |
| `/portfolio/[id]/factors` | `getFactorExposure()` -> `GET /analytics/factor-exposure` | `main.get_factor_exposure` -> `factor_engine.compute_portfolio_factor_exposure`; computed factor projection | `portfolios`, `portfolio_items`, market/agent data through `data_fetcher`; in-process analytics cache | portfolio id query; `FactorExposureResult` | factor exposure, style, sector concentration, drift inputs, per-stock scores, metadata | service-level portfolio-universe aggregation and response projection | Analytics | `MEDIUM` |

Evidence: `M34-E-0028`, `M34-E-0029`, `M34-E-0031`, `M34-E-0035`.

### 2.3 Operations Center and optimizer/intelligence contracts

| Originating surface(s) | Frontend call -> backend endpoint | Service entry / primary read model | Primary source | Transport objects / response DTO | Visible output claims | Known transformations / aggregations | Owner candidate | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/operations-center`, `/optimizer` | `getOperationsStatus()` -> `GET /operations-center/status` | `operations_center.build_operations_status`; cross-source status projection | `portfolios`, `portfolio_snapshots`, `user_execution_decisions`, `optimizer_history`, `recommendation_snapshots`, `benchmark_prices`, regime sources; service TTL cache | portfolio id; `OperationsCenterStatus` | portfolio summary, goal, market context, optimizer/consensus, policy, station health, translation/action state | service composes latest rows, cached regime projection, goal profile, health and translation blocks | Portfolio Intelligence plus source-domain candidates | `MEDIUM` |
| `/operations-center`, `/optimizer` | `getOptimizerProgress()` -> `GET /operations-center/optimizer-progress` | `run_progress.get_progress`; in-memory run projection | per-process in-memory run-progress registry | portfolio id; `OptimizerProgress` | active stage and progress timeline | keyed lookup and response projection | Portfolio Intelligence candidate | `HIGH` |
| `/operations-center`, `/optimizer` | `listOptimizerHistory()` -> `GET /optimizer/history` | `main.list_optimizer_history`; ordered history summary projection | `optimizer_history` | portfolio id; `OptimizerHistoryItem[]` | run dates, status, scores, counts, no-action state | parses selected fields from stored `result_json` and maps summary rows | Optimizer / Portfolio Intelligence candidate | `HIGH` |
| `/operations-center`, `/optimizer` | `getOptimizerHistory()` -> `GET /optimizer/history/{history_id}` | `main.get_optimizer_history_detail`; detailed history projection | `optimizer_history`, `recommendation_snapshots`; current strategy/noise helper inputs | path history id; `OptimizerResult` | recommendation/result detail, policy, consensus, action/execution display projections | parses stored JSON, injects snapshot id, and conditionally derives response-time action/optimization projections | Optimizer / Portfolio Intelligence candidate | `MEDIUM` |
| `/optimizer` | `listStrategyProfiles()` -> `GET /strategy-profiles` | `main.list_strategy_profiles`; constant-map projection | `STRATEGY_PROFILES` in `strategy_profiles.py` | `{profiles: StrategyProfile[]}` | available personas and profile attributes | maps the in-memory constant table to transport dictionaries | Optimizer / configuration candidate | `HIGH` |
| `/optimizer` | `getPortfolioPersona()` -> `GET /portfolios/{portfolio_id}/persona` | `main.get_portfolio_persona` -> `strategy_profiles.get_profile`; persona projection | `portfolios` plus `STRATEGY_PROFILES` | path portfolio id; persona/profile object | current persona and profile | validates stored persona and joins static profile | Portfolio Intelligence / configuration candidate | `HIGH` |
| `/optimizer` | `listExecutionDecisions()` -> `GET /optimizer/decisions` | `main.list_execution_decisions`; ordered decision-row projection | `user_execution_decisions` | portfolio/decision/limit query; `ExecutionDecision[]` | recorded legacy decision labels and metadata | filtering, ordering, row mapping | AI Evaluation / legacy decision-record candidate | `HIGH` |
| `/optimizer`, `/portfolio-intelligence` | `getDecisionMemoryTimeline()` -> `GET /analytics/decision-memory` | `main.get_decision_memory_timeline`; timeline aggregate projection | `user_execution_decisions`, `recommendation_snapshots`, `shadow_portfolios` | portfolio id, limit; `DecisionMemoryEntry[]` | decision timeline, snapshot context, shadow summaries | joins each decision to recommendation JSON fields and related shadow rows | Portfolio Intelligence + AI Evaluation candidates | `HIGH` |
| `/portfolio-intelligence`, `/optimizer` components | `getAIvsHumanTimeline()` -> `GET /analytics/ai-vs-human-timeline` | `main.get_ai_vs_human_timeline` -> `human_vs_ai.compare_human_vs_ai`; timeline projection | `user_execution_decisions`, `portfolio_snapshots`, `shadow_portfolios`, `shadow_portfolio_snapshots` | portfolio id, evaluation days, limit; `AIvsHumanTimeline` | per-decision AI/human comparison and summary | comparison service followed by limit and envelope mapping | Analytics / AI Evaluation candidates | `MEDIUM` |
| `/optimizer` embedded attribution | `getHumanVsAI()` -> `GET /analytics/human-vs-ai` | `main.get_human_vs_ai_comparison` -> `human_vs_ai.compare_human_vs_ai`; comparison projection | same actual/shadow/decision sources as above | portfolio id, evaluation days; `HumanVsAIResponse` | comparison summary and decision rows | service aggregates actual and shadow snapshot series per decision | Analytics / AI Evaluation candidates | `MEDIUM` |
| `/portfolio-intelligence`, `/optimizer`, `/ai-analytics/attribution` | `getAttributionSummary()` -> `GET /analytics/attribution-summary` | `main.get_attribution_summary` -> `attribution_engine`; current/history/waterfall projection | `portfolio_snapshots`, `shadow_portfolios`, `shadow_portfolio_snapshots`, `user_execution_decisions`, `attribution_metrics` | portfolio id, evaluation window; `AttributionSummaryResponse` | actual/shadow results, history, effects, residual/unexplained values | three service reads composed into current, history, and waterfall sections | Analytics | `MEDIUM` |
| `/portfolio-intelligence`, `/optimizer`, `/ai-analytics/attribution` | `getRegimeAttribution()` -> `GET /analytics/regime-attribution` | `main.get_regime_attribution` -> `analytics.regime_attribution.compute_regime_attribution`; regime projection | `portfolio_snapshots`, `regime_snapshots`, `optimizer_history` | portfolio id, lookback days; `RegimeAttributionResponse` | return grouping and optimizer activity by regime | service joins dated snapshot/regime/optimizer records and groups response rows | Analytics | `HIGH` |
| `/portfolio-intelligence`, `/optimizer` | `getConfidenceCalibrationV2()` -> `GET /analytics/confidence-calibration` | `main.get_confidence_calibration_v2` -> `calibration.get_latest_calibration` or `compute_calibration`; calibration envelope | `confidence_calibration_records`; compute fallback reads `signal_history`, `agent_cache`, `regime_snapshots` | portfolio id, lookback, refresh; `EnhancedCalibrationDetail` envelope | calibration result and source classification | cached-record selection or service-computed projection | Portfolio Intelligence / Analytics candidate | `MEDIUM` |
| `/portfolio-intelligence` | `getCalibrationHistory()` -> `GET /analytics/calibration-history` | `main.get_calibration_history`; ordered calibration-row projection | `confidence_calibration_records`, `recommendation_snapshots` for portfolio filter | portfolio id, limit; `CalibrationHistoryEntry[]` | calibration history | resolves portfolio snapshot ids then filters and maps records | Portfolio Intelligence / Analytics candidate | `HIGH` |
| `/portfolio-intelligence`, `/optimizer`, `/ai-analytics/portfolios` | `getShadowPerformanceSummary()` -> `GET /analytics/shadow-performance` | `main.get_shadow_performance_summary` -> `ideal_series.compute_three_portfolios` plus shadow projections | `shadow_portfolios`, `shadow_portfolio_snapshots`, `recommendation_snapshots`, `portfolio_snapshots`, `benchmark_prices`, evaluation settings | portfolio id, period; `ShadowPerformanceSummary` | shadow summaries, Ideal/AI/You series, gaps, risk/return summaries | composes stored shadows with three-portfolio and verdict projections | AI Evaluation + Analytics candidates | `MEDIUM` |
| `/operations-center` | `getTrustReport()` -> `GET /analytics/evaluation/trust-report` | `trust_report.compute_trust_report`; composed sentence projection | sources of scorecard, execution ledger, and scoreboard plus `settings` | portfolio id, period; `TrustReport` | bounded trust-report sentences and link | selects already-returned evaluation fields and composes sentences | AI Evaluation | `MEDIUM` |

Evidence: `M34-E-0028`, `M34-E-0029`, `M34-E-0032`, `M34-E-0033`,
`M34-E-0035`.

### 2.4 AI Evaluation contracts

| Originating surface(s) | Frontend call -> backend endpoint | Service entry / primary read model | Primary source | Transport objects / response DTO | Visible output claims | Known transformations / aggregations | Owner candidate | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/ai-analytics` and Operations Center verdict tile | `getEvaluationScorecard()` -> `GET /analytics/evaluation/scorecard` | `scorecard.compute_scorecard`; three-lens aggregate | `recommendation_grades`, `recommendation_snapshots`, `confidence_calibration_records`, `shadow_portfolios`, `shadow_portfolio_snapshots`, `workspace/settings`; attribution, human-vs-AI, opportunity-cost and ideal-series services | portfolio id, period; `EvaluationScorecard` | belief/execution/outcome lenses, grades, recent grades, verdict | composes persisted grades and shared analytical projections | AI Evaluation | `MEDIUM` |
| `/ai-analytics/recommendations` | `getRecommendationsLedger()` -> `GET /analytics/evaluation/recommendations` | `recommendation_ledger.list_recommendations_ledger`; paged ledger projection | `recommendation_snapshots`, `recommendation_grades`, `user_execution_decisions`, evaluation settings | portfolio id, limit, offset; `RecommendationLedger` | recommendation rows, decisions, horizons, counterfactual flags and headline result | joins snapshots/grades/decisions and creates horizon-strip states | AI Evaluation | `HIGH` |
| `/ai-analytics/recommendations/[id]` | `getRecommendationReportCard()` -> `GET /analytics/evaluation/recommendations/{snapshot_id}` | `recommendation_ledger.get_report_card`; report-card aggregate | sources above plus plan reconstruction and execution-analysis sources, including linked `transactions` when present | path snapshot id, portfolio id; `RecommendationReportCard` | plan, recorded decision, execution analysis, horizon outcomes, verdict | reconstructs stored plan projection and composes plan/decision/execution/outcome sections | AI Evaluation | `MEDIUM` |
| `/ai-analytics/execution` | `getExecutionLedger()` -> `GET /analytics/evaluation/execution` | `execution_ledger.list_execution_ledger`; ledger aggregate | `user_execution_decisions`, `recommendation_snapshots`, `recommendation_grades`, `transactions`, evaluation settings | portfolio id, period; `ExecutionLedger` | decision ledger, class-segmented acceptance, execution/outcome summaries | reconstructs plan inputs, joins decision/grade/transaction data, aggregates summary | AI Evaluation | `MEDIUM` |
| `/ai-analytics/execution/[id]` | `getExecutionDetail()` -> `GET /analytics/evaluation/execution/{decision_id}` | `execution_ledger.get_execution_detail`; decision-detail projection | `user_execution_decisions`, linked `recommendation_snapshots`, `transactions` | path decision id, portfolio id; `ExecutionDetail` | per-symbol planned/actual fields, deltas, completeness and warning | reconstructs plan and maps linked transaction evidence into analysis projection | AI Evaluation | `MEDIUM` |
| `/ai-analytics/human-vs-ai` | `getHumanVsAiScoreboard()` -> `GET /analytics/evaluation/human-vs-ai` | `human_vs_ai.compute_scoreboard`; grade-sourced scoreboard | `user_execution_decisions`, `recommendation_grades`, `workspace/settings` | portfolio id, period; `HumanVsAiScoreboard` | scoreboard, net effect, class and override segments | joins nearest matured grade per decision and groups result buckets | AI Evaluation | `HIGH` |
| `/ai-analytics/opportunity-cost` | `getOpportunityCost()` -> `GET /analytics/evaluation/opportunity-cost` | `opportunity_cost.compute_opportunity_cost`; divergence ledger projection | `user_execution_decisions`, `recommendation_grades`, `recommendation_snapshots`, `portfolio_snapshots` | portfolio id, period; `OpportunityCostLedger` | counterfactual deltas, divergence rows, system deferrals | joins decisions to matured grades and actual snapshot series; projects deferrals | AI Evaluation | `MEDIUM` |
| `/ai-analytics/portfolios` | `getShadowPerformanceSummary()` -> `GET /analytics/shadow-performance` | shared contract recorded in section 2.3 | shared shadow/ideal/actual/benchmark sources | `ShadowPerformanceSummary` | three indexed portfolio series, gaps, summary/risk fields | page selects `three_portfolios` and derives presentation rows from the shared response | AI Evaluation + Analytics candidates | `MEDIUM` |
| `/ai-analytics/attribution` | `getAttributionSummary()` and `getRegimeAttribution()` -> their shared analytics endpoints | shared contracts recorded in section 2.3 | shared attribution and regime sources | `AttributionSummaryResponse`, `RegimeAttributionResponse` | effect waterfall, residual, regime/holding availability views | page selects period/tab projections from two shared responses | Analytics + AI Evaluation presentation candidate | `MEDIUM` |

Evidence: `M34-E-0028`, `M34-E-0029`, `M34-E-0033`, `M34-E-0034`,
`M34-E-0035`.

### 2.5 Portfolio-facing configuration and static explanatory contracts

| Originating surface(s) | Frontend call -> backend endpoint | Service entry / primary read model | Primary source | Transport objects / response DTO | Visible output claims | Known transformations / aggregations | Owner candidate | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/settings` | `getSectorLimits()` -> `GET /settings/sector-limits` | `main._get_sector_limits`; configuration projection | `settings` plus code defaults | `SectorLimits` | sector allocation limits | saved values merged over defaults | Configuration/governance candidate | `HIGH` |
| `/settings` | `getPortfolioSettings()` -> `GET /settings/portfolio` | `main._get_portfolio_settings`; configuration projection | `settings` plus code defaults | `PortfolioSettings` | portfolio count/concentration settings | saved values merged over defaults | Configuration/governance candidate | `HIGH` |
| `/settings` | `getOptimizerLayers()` -> `GET /settings/optimizer-layers` | `main._get_optimizer_layers`; configuration projection | `settings` plus optimizer defaults | `OptimizerLayers` | layer provider/model selection | saved values merged over defaults | Optimizer configuration candidate | `HIGH` |
| `/settings` | `getOptimizerFallback()` -> `GET /settings/optimizer-fallback` | `main._get_optimizer_fallback`; configuration projection | `settings` plus code defaults | `OptimizerFallback` | fallback provider/model | saved value or default projection | Optimizer configuration candidate | `HIGH` |
| `/settings` | `getAnalysisSources()` -> `GET /settings/analysis-sources` | `main._get_analysis_sources`; configuration projection | `settings` plus code defaults | `AnalysisSources` | enabled technical/fundamental/news sources | saved value or default projection | Stock/AI-analysis configuration candidate | `HIGH` |
| `/system-guide` | `NONE` -> static route content | `frontend/app/system-guide/page.tsx`; static repository projection | repository source in the route file | no API/DTO | navigation and capability explanations | local tab selection only | Documentation + Experience presentation candidates | `HIGH` |

`getAIModels()` and `getAISettings()` are recorded in section 2.1 because
they are shared with `/stock/[symbol]`.

Evidence: `M34-E-0028`, `M34-E-0029`, `M34-E-0030`, `M34-E-0035`.

## 3. Frontend to Backend Contract Map

```text
Shared scope
  listPortfolios                         -> GET /portfolios

Portfolio / market / instrument
  getHoldings                            -> GET /portfolios/{id}/holdings
  getPortfolioPrices                     -> GET /portfolios/{id}/prices
  getSectorBreakdown                     -> GET /portfolios/{id}/sector-breakdown
  getWatchlist                           -> GET /watchlist
  getStockQuick                          -> GET /stocks/{symbol}
  getStockChart                          -> GET /stocks/{symbol}/chart
  getAnalysisHistory                     -> GET /analysis/history/{symbol}
  getConsensus                           -> GET /analyze/{symbol}/consensus

Snapshot / analytics
  getSnapshots                           -> GET /portfolios/{id}/snapshots
  getPerformanceComparison               -> GET /analytics/performance-comparison
  getPerformanceStats                    -> GET /analytics/performance-stats
  getFactorExposure                      -> GET /analytics/factor-exposure

Operations / optimizer / intelligence
  getOperationsStatus                    -> GET /operations-center/status
  getOptimizerProgress                   -> GET /operations-center/optimizer-progress
  listOptimizerHistory                   -> GET /optimizer/history
  getOptimizerHistory                    -> GET /optimizer/history/{id}
  listStrategyProfiles                   -> GET /strategy-profiles
  getPortfolioPersona                    -> GET /portfolios/{id}/persona
  listExecutionDecisions                 -> GET /optimizer/decisions
  getDecisionMemoryTimeline              -> GET /analytics/decision-memory
  getAIvsHumanTimeline                   -> GET /analytics/ai-vs-human-timeline
  getHumanVsAI                           -> GET /analytics/human-vs-ai
  getAttributionSummary                  -> GET /analytics/attribution-summary
  getRegimeAttribution                   -> GET /analytics/regime-attribution
  getConfidenceCalibrationV2             -> GET /analytics/confidence-calibration
  getCalibrationHistory                  -> GET /analytics/calibration-history
  getShadowPerformanceSummary            -> GET /analytics/shadow-performance
  getTrustReport                         -> GET /analytics/evaluation/trust-report

AI Evaluation
  getEvaluationScorecard                 -> GET /analytics/evaluation/scorecard
  getRecommendationsLedger               -> GET /analytics/evaluation/recommendations
  getRecommendationReportCard            -> GET /analytics/evaluation/recommendations/{snapshot_id}
  getExecutionLedger                     -> GET /analytics/evaluation/execution
  getExecutionDetail                     -> GET /analytics/evaluation/execution/{decision_id}
  getHumanVsAiScoreboard                 -> GET /analytics/evaluation/human-vs-ai
  getOpportunityCost                     -> GET /analytics/evaluation/opportunity-cost

Configuration
  getAIModels                            -> GET /ai-models
  getAISettings                          -> GET /settings/ai-models
  getAnalysisSources                     -> GET /settings/analysis-sources
  getSectorLimits                        -> GET /settings/sector-limits
  getPortfolioSettings                   -> GET /settings/portfolio
  getOptimizerLayers                     -> GET /settings/optimizer-layers
  getOptimizerFallback                   -> GET /settings/optimizer-fallback

Static
  /system-guide                          -> repository route content; no API
```

The map contains 43 unique `GET` endpoints. Shared consumers do not create a
second contract. Evidence: `M34-E-0028`, `M34-E-0029`.

## 4. Backend Service Inventory

| Service entry or handler family | Contracts supplied | Immediate read model | Source boundary observed |
| --- | --- | --- | --- |
| `main.list_portfolios`, `list_holdings`, `get_portfolio_prices`, `get_sector_breakdown` | selected scope, holdings, quotes, sectors | handler-built row and join projections | Portfolio/holding/configuration/cache rows plus quote provider path |
| `data_fetcher.fetch_price_info` and `fetch_history`; `chart_data.fetch_chart_data` | price and chart contracts | quote/history cache or provider projection | `MarketDataCache` with configured provider fallback |
| `main.list_watchlist`, `get_stock_quick`, `get_analysis_history`, `get_consensus` | watchlist and stock investigation | enriched row/agent/history projections | watchlist and analysis caches/history plus market/registry paths |
| `main.list_snapshots`, `get_performance_comparison` | snapshot and comparative performance reads | snapshot rows and chart-ready aggregate | portfolio snapshots and benchmark prices |
| `analytics.quant_engine` builders | performance-stats contract | computed aggregate dictionary | caller-supplied snapshots, benchmark map, and signal rows; in-process cache |
| `analytics.factor_engine.compute_portfolio_factor_exposure` | factor contract | computed factor dictionary | portfolio holdings plus market/agent inputs; in-process cache |
| `operations_center.build_operations_status` | operations status | composed status dictionary | portfolio, snapshot, decision, optimizer, recommendation, benchmark and regime sources |
| `run_progress.get_progress` | optimizer progress | in-memory progress dictionary | per-process registry |
| optimizer history/persona handlers and strategy-profile helpers | optimizer history, detail, profile, persona | ORM/JSON/config projections | optimizer history, recommendation snapshot, portfolio and static profile map |
| decision-memory handlers and `analytics.attribution_engine`, `human_vs_ai`, `regime_attribution`, `decision_memory.calibration` | timeline, attribution, comparisons, regime, calibration | computed or persisted analytical projections | decision, recommendation, shadow, portfolio snapshot, regime, grade/calibration sources |
| `evaluation.ideal_series.compute_three_portfolios` plus shadow handler | shadow and three-portfolio contract | combined shadow/ideal/actual projection | recommendation, portfolio/shadow snapshot, benchmark and settings sources |
| `evaluation.scorecard`, `recommendation_ledger`, `execution_ledger`, `opportunity_cost`, `trust_report` and `human_vs_ai.compute_scoreboard` | seven evaluation endpoints plus trust report | evaluation aggregates | grades, recommendations, decisions, transactions, shadows, snapshots and settings |
| settings helper functions and `get_ai_models` | configuration contracts | saved/default configuration projection | `Settings` rows or `backend/ai-model.json` |

Evidence: `M34-E-0029` through `M34-E-0034`.

## 5. Persistence Source Inventory

| Source | Read by current WP4 contracts | Immediate role in observable lineage |
| --- | --- | --- |
| `portfolios` (`Portfolio`) | scope, persona, operations, performance/factor validation | portfolio identity, name, cash/goal/persona fields |
| `portfolio_items` (`PortfolioItem`) | holdings, prices, sectors, factors | current holding rows and sector/cost inputs |
| `watchlist` (`Watchlist`) | watchlist | monitored symbols and registry binding |
| `agent_cache` (`AgentCache`) | holdings/watchlist enrichment, stock quick, factors, calibration | stored technical/fundamental/news projections and target data |
| `analysis_cache` (`AnalysisCache`) | holdings, watchlist, stock quick | latest consolidated analysis projection |
| `analysis_history` (`AnalysisHistory`) | stock history and consensus; holdings consensus helper | retained analysis events and latest-day consensus inputs |
| `market_data_cache` (`MarketDataCache`) | prices, stock/chart data, factor inputs | cached quote/fundamental/history payloads before provider fallback |
| `portfolio_snapshots` (`PortfolioSnapshot`) | performance, analytics, attribution, human/AI, regime, ideal series | dated portfolio value/return/holdings projections |
| `benchmark_prices` (`BenchmarkPrice`) | performance comparison/stats, operations recency, ideal/shadow projections | retained benchmark observations |
| `signal_history` (`SignalHistory`) | performance stats and calibration | retained signal observations |
| `optimizer_history` (`OptimizerHistory`) | optimizer history/detail, operations, regime attribution | persisted optimizer-result JSON and run summary fields |
| `recommendation_snapshots` (`RecommendationSnapshot`) | decision memory, shadow/ideal, all evaluation ledgers | frozen optimizer-era recommendation projections and linked JSON sections |
| `user_execution_decisions` (`UserExecutionDecision`) | optimizer legacy decisions, decision memory, attribution/comparison, evaluation | recorded legacy decision labels and links |
| `transactions` (`Transaction`) | evaluation report/execution detail and ledger | transactions linked to a legacy decision when present |
| `shadow_portfolios` (`ShadowPortfolio`) | attribution, human/AI, shadow performance, scorecard | shadow identity and current summary fields |
| `shadow_portfolio_snapshots` (`ShadowPortfolioSnapshot`) | attribution, human/AI, shadow/three-portfolio views | dated shadow value/return/benchmark projections |
| `attribution_metrics` (`AttributionMetric`) | attribution history | persisted attribution projections |
| `regime_snapshots` (`RegimeSnapshot`) | regime detection/attribution and calibration | dated regime observations |
| `recommendation_grades` (`RecommendationGrade`) | scorecard and all evaluation ledgers | persisted plan/horizon grade projections |
| `confidence_calibration_records` (`ConfidenceCalibrationRecord`) | scorecard and calibration/history | persisted calibration projections |
| `settings` (`Settings`) | portfolio/sector/AI/optimizer/evaluation configuration | workspace-keyed JSON/scalar configuration plus code defaults |
| `backend/ai-model.json` | AI model list | static provider/model catalogue |
| in-process analytics/regime/progress caches | analytics, operations regime, optimizer progress | non-persistent response reuse or current per-process progress |
| configured market/agent/provider calls | price, chart, stock/factor paths when local persistence cannot supply the response | external response input; no runtime provider observation was collected |

This table records source participation only. It does not rank sources,
declare canonical truth, or assess persistence design. Evidence:
`M34-E-0030` through `M34-E-0035`.

## 6. Transformation Inventory

| Location | Observed transformation or aggregation | Contracts affected | Classification limit |
| --- | --- | --- | --- |
| `PortfolioContext` | validates a browser-saved active id against `listPortfolios()` and otherwise selects the first returned portfolio | shared scope | Selection behavior only; no authorization or semantic ruling |
| root dashboard | fans out holdings/prices across portfolios, groups visible positions by symbol, and assembles heatmap rows | holdings/prices | Client composition is recorded, not assessed |
| portfolio overview and summary/table components | merges price responses into holding rows and derives displayed summary/table projections | holdings/prices/sectors | No formula or valuation judgment |
| performance page/components | selects snapshot fields and comparison series for summary, history, and charts | snapshots/comparison | Presentation projection only |
| analytics page and `analytics-transformers.ts` | maps backend metric arrays into heatmap, decay, contribution, comparison, and chart props | performance stats/comparison | No metric interpretation or correctness decision |
| stock/watchlist pages | resolves/filter/sorts visible response rows and composes quick result, chart, history, consensus, and configuration | stock/watchlist contracts | No source freshness or quality judgment |
| `main.py` portfolio/market handlers | joins ORM rows, JSON caches, quote results, registry projections, and code defaults into transport dictionaries | portfolio/stock/watchlist/settings | Handler composition only |
| performance/factor/analytics services | aggregate retained snapshots, benchmark rows, signals, holdings, and factor inputs into response dictionaries | performance/factor contracts | Function presence and source lineage only |
| operations service | selects latest source rows and composes portfolio, goal, market, optimizer, policy, health, and translated status blocks | operations status | Does not appoint the aggregator as semantic owner |
| optimizer-history detail handler | parses stored result JSON and conditionally adds current response-time action/optimization projections | optimizer detail | Historical/current semantic equivalence is not assessed |
| portfolio-intelligence page/components | combines timeline, attribution, calibration, regime, decision-memory, and shadow responses into panels | intelligence contracts | Shared labels do not prove shared semantics |
| attribution/comparison/calibration services | join portfolio, shadow, decision, regime, and calibration sources into analytical projections | intelligence and attribution | No formula or trust assessment |
| evaluation services | join grades, recommendations, decisions, transactions, shadows, snapshots, settings, and shared analytical services into ledgers/lenses | AI Evaluation contracts | No grade, return, counterfactual, or owner judgment |
| evaluation pages/components | filter, paginate, select periods/tabs, and map response sections into tables/charts/cards | AI Evaluation contracts | No backend metric is treated as verified by presentation |
| settings page | initializes editable form state from configuration responses | settings contracts | Write behavior and policy ownership are outside WP4 |
| System Guide | selects static tabs and renders repository-authored explanatory text | static guide | Documentation claim only |

Evidence: `M34-E-0036`.

## 7. Read Lineage Map

```text
WP3 portfolio-facing surface
        |
        v
frontend route / directly rendered component
        |
        +-- shared PortfolioContext -> listPortfolios -> GET /portfolios
        |
        v
frontend/lib/api.ts function + TypeScript response interface
        |
        v
FastAPI GET handler in backend/main.py
        |
        +-- direct ORM/config/in-memory projection
        |       -> Portfolio / holding / cache / settings / history rows
        |
        +-- source-domain service projection
        |       -> market-data, snapshots, quantitative/factor analytics
        |
        +-- cross-source composition service
                -> operations, decision-memory, shadow/attribution,
                   evaluation ledgers and scorecards
        |
        v
handler-built dict/list transport
        |
        v
frontend selection / formatting / chart-table projection
        |
        v
visible WP3 output claim
```

The transport layer copies or composes source fields but is not promoted to a
new read-model domain. Evidence: `M34-E-0037`.

## 8. Cross-domain Read Dependencies

| Consumer candidate | Observed read dependencies | Surfaces |
| --- | --- | --- |
| Experience | all response contracts plus shared active-portfolio selection | all 22 WP3 surfaces |
| Portfolio read composition | Ledger-derived holding rows, Market Data quotes, cached analysis, configuration | `/`, `/portfolio` |
| Analytics | portfolio snapshots, benchmarks, signal history, holdings and market/agent inputs | `/performance`, `/analytics`, factors and downstream consumers |
| Portfolio Intelligence / Optimizer | portfolio/snapshot state, market regime, analysis caches, recommendation history, decisions, analytics and configuration | Operations Center, Optimizer, Portfolio Intelligence |
| AI Evaluation | recommendation snapshots/grades, legacy decisions, transactions, portfolio/shadow snapshots, benchmarks, settings, shared analytics | nine AI Evaluation routes plus operations trust/verdict tiles |
| Watchlist / stock analysis | watchlist rows, market cache/provider, agent/analysis caches, registry projections and AI configuration | Watchlist and stock detail |
| Documentation/configuration | settings rows, static defaults/model catalogue, repository guide content | Settings and System Guide |

These are dependency observations, not ownership decisions. Evidence:
`M34-E-0037`.

## 9. Shared Contract Candidates

| Candidate contract | Observed consumers | Why it is a shared-contract candidate | What remains for WP5 |
| --- | --- | --- | --- |
| `listPortfolios` / active scope | most portfolio-scoped routes | one provider supplies portfolio selection | scope meaning and authority are not verified |
| holdings + portfolio prices | root dashboard and portfolio overview | same two responses feed cross-portfolio and selected-portfolio views | field meaning and client derivations require verification |
| snapshots + performance comparison | Performance and Analytics | shared historical/value and benchmark inputs | period, basis, and label equivalence require verification |
| optimizer history/detail | Operations Center and Optimizer | same stored run summaries/details are rendered in both contexts | live/history projection relationship remains unverified |
| operations status | Operations Center and Optimizer | one composite response supplies status/policy context | source-field authority must be verified separately |
| attribution summary | Portfolio Intelligence, Optimizer, AI Evaluation Attribution | one endpoint supplies several panels | effect/residual/history meanings require verification |
| regime attribution | Portfolio Intelligence, Optimizer, AI Evaluation Attribution | one endpoint supplies grouped regime outputs | period and comparison semantics require verification |
| decision memory + AI/human timeline | Optimizer and Portfolio Intelligence | shared decision-history projections | relationship among timelines and legacy decision vocabulary requires verification |
| shadow performance | Optimizer, Portfolio Intelligence, AI Evaluation Portfolio Comparison | one response supplies shadow summary and three-portfolio projection | shared and distinct meanings require verification |
| evaluation scorecard | AI Evaluation Scorecard and Operations Center verdict tile | one response is presented in detailed and summary contexts | summary selection and explanation require verification |
| AI model/settings contracts | Settings and stock detail | one catalogue/selection pair configures several consumers | configuration meaning and fallback behavior require verification |
| cached stock-analysis projections | holdings, watchlist, stock detail | several responses reuse analysis/agent cache fields | whether fields are semantically identical remains unverified |

Candidates are not duplicate concepts or approved shared contracts. Evidence:
`M34-E-0037`.

## 10. Lineage Unknowns

| ID | Unknown | Boundary preserved by WP4 |
| --- | --- | --- |
| `L01` | Whether consumer TypeScript interfaces and handler-built dictionaries are field-complete equivalents in every branch | No generated schema or runtime payload comparison was executed |
| `L02` | Runtime provider, cache-hit, stale-fallback, and network path used for any price/chart/agent response | Static code exposes alternatives; no runtime evidence selects one |
| `L03` | Complete versioned schema of JSON stored in analysis, optimizer, recommendation, grade-detail, and settings fields | WP4 records parsing sites but does not invent missing schemas |
| `L04` | Whether client-composed portfolio summaries have a single authoritative backend read contract | WP4 traces inputs and transformation locations only |
| `L05` | Whether response-time optimizer detail projections are equivalent to the original live-run response or original run-time policy | No semantic or historical comparison is permitted in WP4 |
| `L06` | Whether similarly named attribution, human/AI, performance, and portfolio-comparison fields share a definition | Shared sources/labels do not prove semantic identity |
| `L07` | Whether current GET handlers that call compute/repair helpers cause persistence changes in every branch | WP4 does not execute or assess side effects; it records only the reachable source path |
| `L08` | Runtime consistency of in-process analytics, regime, and optimizer-progress state across deployed processes | No runtime/topology observation was collected |
| `L09` | Completeness of registry persistence behind `registry_lookup` in the watchlist projection | The helper boundary is observed; registry redesign and semantic audit are excluded here |
| `L10` | Whether every component-level response field has the same period, benchmark, as-of time, and optionality as a similarly titled field elsewhere | WP5 must verify field-level contracts |
| `L11` | Whether command-only transient results shown before a later GET are identical to their persisted read projection | Command responses are not relabeled as read contracts |
| `L12` | Whether runtime-only, feature-flagged, or external read contracts exist beyond the frozen WP3 route corpus | Static repository scope cannot prove external absence |
| `L13` | Final semantic owner of every cross-source composite | WP4 retains WP3 candidates and makes no ownership decision |
| `L14` | Correctness, formula, valuation, freshness, trust, and failure meaning of every inventoried field | Explicitly deferred to later M34 verification |

Unknowns do not reduce to assumptions and do not support readiness.

## 11. Read Contract Completeness Assessment

| Completeness dimension | Result | Basis |
| --- | --- | --- |
| Frozen WP3 surface coverage | Complete | all 22 included surfaces accounted for without changing the route inventory |
| Material HTTP read population | Complete for audited revision | 43 unique `GET` endpoints mapped from current frontend consumers |
| Static portfolio-facing content | Complete for audited revision | System Guide recorded as the only no-API explanatory surface; Goal Wizard has only shared scope read |
| Frontend-to-endpoint mapping | Complete | every included contract has an exported client call or explicit static boundary |
| Handler/service entry mapping | Complete | each HTTP contract resolves to a named handler and, where present, a named service entry |
| Primary read model/source mapping | Complete at observable static depth | concrete ORM tables, config files/defaults, caches, provider boundaries, or in-memory state recorded |
| Transport/response DTO mapping | Complete | frontend TypeScript response shapes and raw backend dict/list boundary recorded |
| Known transformation/aggregation locations | Complete at contract level | route, handler, and service composition sites identified without calculation assessment |
| Candidate ownership | Preserved, not decided | WP3 candidates carried forward only |
| Runtime lineage | Not collected | no runtime execution authorized |
| Semantic/correctness/freshness/trust verification | Intentionally incomplete | WP5 entry work, not a WP4 criterion |
| Findings and decisions | None | WP4 prohibits both |

Evidence: `M34-E-0038`.

## 12. Recommendation for WP5

**Yes — the read-contract inventory is complete enough for WP5.**

WP5 now has a closed surface population, 43 concrete HTTP read contracts, one
static content contract, named transport types, handler/service entries,
primary source participation, transformation locations, cross-domain
dependencies, shared-contract candidates, and explicit unknowns.

The recommendation has five conditions:

1. WP5 must verify field-level authority and meaning; it must not treat a raw
   handler dictionary or TypeScript interface as semantic proof.
2. WP5 must verify shared labels independently across periods, benchmarks,
   timestamps, optionality, provenance, and source-domain definitions.
3. WP5 must retain external/provider and JSON-schema gaps as unknown until
   evidence resolves them.
4. WP5 must treat all owner labels here as candidates and return ownership
   conflicts to the approved review process.
5. WP5 must preserve `STOP_M33_RUNTIME`; legacy decision/execution-labelled
   reads may be audited as current product claims but cannot authorize or
   adopt stopped runtime work.

This recommendation does not authorize M34.1. M34.1 remains NO-GO.

## 13. Register Impact

- New corpus records: `M34-C-0040` through `M34-C-0048`.
- New verified evidence records: `M34-E-0028` through `M34-E-0038`.
- New verification events: `M34-R-0009` through `M34-R-0011`.
- Findings created: zero.
- Decisions approved: zero. The WP4 recommendation is a work-package handoff
  assessment, not an Architecture Review Board or M34 exit decision.
- Runtime or test evidence collected: zero.

## 14. Explicit Non-Adoption Statement

M34-WP4 does not:

- judge semantic correctness, calculations, formulas, valuation, freshness,
  trust, failure meaning, implementation quality, or product usefulness;
- appoint an owner, approve a shared contract, or classify two contracts as
  semantically identical;
- redesign a route, API, DTO, service, persistence model, cache, provider,
  transformation, or domain boundary;
- create a finding, disposition, decision, Decision Log entry, or M34 exit;
- execute an endpoint, query a runtime database, call a provider, or run a
  test suite;
- modify frontend, backend, database, API, tests, configuration, or runtime;
- propose Portfolio Home or implementation work;
- authorize identity, approval, execution-intent, certificate, execution, or
  other stopped M33 runtime work;
- reopen M32 or M33; or
- authorize M34.1.

M34.1 remains NO-GO.
