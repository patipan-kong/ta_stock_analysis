import { getToken, logout } from "@/lib/auth";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  // Spread init first so caller options (method, body, etc.) are set, then
  // override headers last so Authorization is never clobbered by init.headers.
  const { headers: callerHeaders, ...restInit } = init ?? {};
  const res = await fetch(`${BASE_URL}${path}`, {
    ...restInit,
    headers: {
      "Content-Type": "application/json",
      ...(callerHeaders as Record<string, string> | undefined),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (res.status === 401) {
    logout();
    throw new Error("Session expired");
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ─── Types ───────────────────────────────────────────────────────────────────

export interface Portfolio {
  id: number;
  name: string;
  cash_balance: number;
  goal_target_value?: number | null;
  created_at: string;
}

export const updatePortfolioGoal = (portfolioId: number, goal: number | null) =>
  apiFetch<{ id: number; goal_target_value: number | null; ok: boolean }>(
    `/portfolios/${portfolioId}/goal`,
    { method: "PATCH", body: JSON.stringify({ goal_target_value: goal }) },
  );

// ─── Goal Profile (Phase 4C.3 Goal Discovery Wizard) ─────────────────────────

export type GoalType =
  | "WEDDING"
  | "HOUSE"
  | "EDUCATION"
  | "RETIREMENT"
  | "FINANCIAL_FREEDOM"
  | "WEALTH_GROWTH"
  | "OTHER";

export type GoalPriority = "ESSENTIAL" | "IMPORTANT" | "ASPIRATIONAL";

export type RiskPersonality = "AGGRESSIVE" | "MODERATE" | "CONSERVATIVE";

export interface GoalProfile {
  portfolio_id: number | null;
  configured: boolean;
  goal_type: GoalType | null;
  goal_emoji: string | null;
  goal_label_th: string | null;
  goal_target_value: number | null;
  goal_target_date: string | null; // YYYY-MM-DD
  goal_priority: GoalPriority | null;
  goal_priority_label_th: string | null;
  risk_personality: RiskPersonality | null;
  risk_personality_label_th: string | null;
}

export interface GoalProfileUpdate {
  goal_type?: GoalType | null;
  goal_priority?: GoalPriority | null;
  goal_target_date?: string | null;
  risk_personality?: RiskPersonality | null;
  goal_target_value?: number | null;
}

export const getGoalProfile = (portfolioId: number) =>
  apiFetch<GoalProfile>(`/portfolios/${portfolioId}/goal-profile`);

export const updateGoalProfile = (portfolioId: number, update: GoalProfileUpdate) =>
  apiFetch<GoalProfile>(`/portfolios/${portfolioId}/goal-profile`, {
    method: "PUT",
    body: JSON.stringify(update),
  });

export type RiskLevel = "Low" | "Medium" | "High" | "Critical";

export interface PortfolioItem {
  id: number;
  portfolio_id: number;
  symbol: string;
  shares: number;
  avg_cost: number;
  current_price: number | null;
  change_percent: number | null;
  last_updated: string | null;
  latest_signal: "ACCUMULATE" | "BUY" | "WATCH" | "HOLD" | "REDUCE" | "SELL" | null;
  signal_confidence: "high" | "medium" | "low" | null;
  analyzed_at: string | null;
  reasoning: string | null;
  risks: string | null;
  ta_score: number | null;
  fa_score: number | null;
  allow_swap: boolean;
  target_price: number | null;
  upside_pct: number | null;
  risk_level: RiskLevel | null;
  sector?: string | null;
  is_dr?: boolean;
  parent_symbol?: string | null;
  upside_reference_price?: number | null;
}

export interface WatchlistItem {
  id: number;
  symbol: string;
  latest_signal: "ACCUMULATE" | "BUY" | "WATCH" | "HOLD" | "REDUCE" | "SELL" | null;
  signal_confidence: "high" | "medium" | "low" | null;
  analyzed_at: string | null;
  reasoning: string | null;
  risks: string | null;
  ta_score: number | null;
  fa_score: number | null;
  target_price: number | null;
  upside_pct: number | null;
  risk_level: RiskLevel | null;
  sector?: string | null;
  is_dr?: boolean;
  parent_symbol?: string | null;
  upside_reference_price?: number | null;
}

export interface SectorBreakdownItem {
  sector: string;
  value: number;
  weight_pct: number;
  stocks: string[];
  limit_pct: number;
  status: "OK" | "WARNING" | "EXCEEDS";
}

export interface SectorBreakdown {
  sectors: SectorBreakdownItem[];
  total_value: number;
}

export const getSectorBreakdown = (portfolioId: number) =>
  apiFetch<SectorBreakdown>(`/portfolios/${portfolioId}/sector-breakdown`);

export interface TimeframeTA {
  period: string;
  score: number;
  rsi: number | null;
  macd_signal: string;
  bb_position: string;
  trend: string;
  summary: string;
  error?: string;
}

export interface TechnicalResult {
  symbol: string;
  rsi: number | null;
  macd_signal: string;
  bb_position: string;
  trend: string;
  ta_score: number;
  ta_summary: string;
  short_term?: TimeframeTA;
  long_term?: TimeframeTA;
  error?: string;
}

export interface FundamentalResult {
  symbol: string;
  pe_ratio: number | null;
  eps: number | null;
  revenue_growth: number | null;
  roe: number | null;
  debt_equity: number | null;
  market_cap: number | null;
  target_price: number | null;
  analyst_count: number | null;
  upside_pct: number | null;
  upside_source: string | null;
  fa_score: number;
  fa_summary: string;
  is_dr?: boolean;
  parent_symbol?: string | null;
  upside_reference_price?: number | null;
  error?: string;
}

export interface NewsItem {
  title: string;
  publisher: string;
  link: string;
  published: string;
}

export interface NewsResult {
  symbol: string;
  news: NewsItem[];
  news_count: number;
  error?: string;
}

export interface SummaryResult {
  symbol: string;
  signal: "ACCUMULATE" | "BUY" | "WATCH" | "HOLD" | "REDUCE" | "SELL";
  confidence: "high" | "medium" | "low";
  reasoning: string;
  risks: string;
  executive_summary?: string | null;
  ai_summary?: string | null;
  analyzed_at?: string | null;
  from_cache?: boolean;
  ai_provider?: string | null;
  ai_model?: string | null;
  history_id?: number | null;
  error?: string;
}

export interface AnalysisScores {
  technical_score: number;
  fundamental_score: number;
  news_sentiment: number;
  risk_score: number;
}

export interface AnalysisHistoryItem {
  id: number;
  symbol: string;
  signal: "ACCUMULATE" | "BUY" | "WATCH" | "HOLD" | "REDUCE" | "SELL";
  confidence: "high" | "medium" | "low";
  reasoning: string;
  risks: string;
  executive_summary?: string | null;
  ai_summary?: string | null;
  ta_score: number | null;
  fa_score: number | null;
  ai_provider: string | null;
  ai_model: string | null;
  sources_used: SourcesUsed | null;
  scores: AnalysisScores | null;
  analyzed_at: string;
}

export interface ConsensusResult {
  symbol: string;
  consensus_signal: "ACCUMULATE" | "BUY" | "WATCH" | "HOLD" | "REDUCE" | "SELL";
  agreement: number;
  high_disagreement: boolean;
  total_analyses: number;
  signal_counts: { ACCUMULATE: number; BUY: number; WATCH: number; HOLD: number; REDUCE: number; SELL: number };
  breakdown: AnalysisHistoryItem[];
  error?: string;
}

export interface WhyDisagreeResult {
  symbol: string;
  synthesis: string;
  key_differences: string[];
  most_defensible: string;
  error?: string;
}

export interface AnalysisSources {
  use_ta: boolean;
  use_fa: boolean;
  use_news: boolean;
}

export interface SourcesUsed {
  ta: boolean;
  fa: boolean;
  news: boolean;
}

export interface FullAnalysis {
  symbol: string;
  technical: TechnicalResult | null;
  fundamental: FundamentalResult | null;
  news: NewsResult | null;
  summary: SummaryResult | null;
  has_cached_summary?: boolean;
  sources_used?: SourcesUsed | null;
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export const loginApi = (username: string, password: string) =>
  fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  }).then(async (res) => {
    if (!res.ok) throw new Error("Invalid credentials");
    return res.json() as Promise<{ token: string; username: string }>;
  });

// ─── Portfolios ───────────────────────────────────────────────────────────────

export const listPortfolios = () => apiFetch<Portfolio[]>("/portfolios");

export const createPortfolio = (name: string) =>
  apiFetch<Portfolio>("/portfolios", { method: "POST", body: JSON.stringify({ name }) });

export const deletePortfolio = (id: number) =>
  apiFetch<{ deleted: number }>(`/portfolios/${id}`, { method: "DELETE" });

export const updatePortfolioCash = (id: number, cash_balance: number) =>
  apiFetch<{ id: number; cash_balance: number }>(`/portfolios/${id}/cash`, {
    method: "PATCH",
    body: JSON.stringify({ cash_balance }),
  });

// ─── Holdings ────────────────────────────────────────────────────────────────

export const getHoldings = (portfolioId: number) =>
  apiFetch<PortfolioItem[]>(`/portfolios/${portfolioId}/holdings`);

export interface PriceRefreshItem {
  symbol: string;
  current_price: number | null;
  change_percent: number | null;
  last_updated: string | null;
  upside_pct?: number | null;
}

export const getPortfolioPrices = (portfolioId: number) =>
  apiFetch<PriceRefreshItem[]>(`/portfolios/${portfolioId}/prices`);

export const addHolding = (portfolioId: number, symbol: string, shares: number, avg_cost: number) =>
  apiFetch<PortfolioItem>(`/portfolios/${portfolioId}/holdings`, {
    method: "POST",
    body: JSON.stringify({ symbol, shares, avg_cost }),
  });

export const removeHolding = (portfolioId: number, symbol: string) =>
  apiFetch<{ deleted: string }>(
    `/portfolios/${portfolioId}/holdings/${encodeURIComponent(symbol)}`,
    { method: "DELETE" }
  );

export const analyzeHoldings = (portfolioId: number) =>
  apiFetch<FullAnalysis[]>(`/portfolios/${portfolioId}/analyze`, { method: "POST" });

export interface AnalyzeAllResult {
  total: number;
  analyzed: number;
  skipped: number;
  results: FullAnalysis[];
  skipped_symbols: string[];
}

export const analyzePortfolioAll = (portfolioId: number) =>
  apiFetch<AnalyzeAllResult>(`/portfolios/${portfolioId}/analyze/all`, { method: "POST" });

export const analyzeWatchlistAll = () =>
  apiFetch<AnalyzeAllResult>(`/watchlist/analyze/all`, { method: "POST" });

// ─── Job-based async analysis ─────────────────────────────────────────────────

export interface JobStartResponse {
  job_id: string;
  status: "queued";
  total: number;
  stale: number;
}

export interface JobStatusResponse {
  job_id: string;
  status: "queued" | "running" | "done" | "failed";
  total: number;
  done: number;
  skipped: number;
  fallbacks: number;
  progress_pct: number;
  results: FullAnalysis[];
}

export const startWatchlistAnalysisJob = () =>
  apiFetch<JobStartResponse>("/analyze/watchlist", { method: "POST" });

export const getAnalysisJob = (jobId: string) =>
  apiFetch<JobStatusResponse>(`/analyze/jobs/${jobId}`);

export async function* streamAnalysisJob(jobId: string): AsyncGenerator<StreamEvent> {
  const token = getToken();
  const response = await fetch(`${BASE_URL}/analyze/jobs/${jobId}/stream`, {
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  });
  if (response.status === 401) { logout(); throw new Error("Session expired"); }
  if (!response.ok || !response.body) throw new Error(`API ${response.status}`);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // SSE format: split on double-newline event boundaries
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";
    for (const event of events) {
      const dataLine = event.trim();
      if (dataLine.startsWith("data: ")) {
        const json = dataLine.slice(6).trim();
        if (json) yield JSON.parse(json) as StreamEvent;
      }
    }
  }
}

// ─── Streaming analyze types ──────────────────────────────────────────────────

export interface StreamStartEvent {
  type: "start";
  total: number;
  stale: number;
  skipped: number;
}
export interface StreamProgressEvent {
  type: "progress";
  done: number;
  total: number;
  result: FullAnalysis & { ai_fallback_used?: boolean };
}
export interface StreamCompleteEvent {
  type: "complete";
  total: number;
  analyzed: number;
  skipped: number;
  fallbacks: number;
}
export type StreamEvent = StreamStartEvent | StreamProgressEvent | StreamCompleteEvent;

export async function* analyzeWatchlistStream(): AsyncGenerator<StreamEvent> {
  const token = getToken();
  const response = await fetch(`${BASE_URL}/watchlist/analyze/all/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (response.status === 401) { logout(); throw new Error("Session expired"); }
  if (!response.ok || !response.body) throw new Error(`API ${response.status}`);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed) yield JSON.parse(trimmed) as StreamEvent;
    }
  }
  if (buffer.trim()) yield JSON.parse(buffer.trim()) as StreamEvent;
}

// ─── Watchlist ───────────────────────────────────────────────────────────────

export const getWatchlist = () => apiFetch<WatchlistItem[]>("/watchlist");

export const addToWatchlist = (symbol: string) =>
  apiFetch<WatchlistItem>("/watchlist", { method: "POST", body: JSON.stringify({ symbol }) });

export const removeFromWatchlist = (symbol: string) =>
  apiFetch<{ deleted: string }>(`/watchlist/${symbol}`, { method: "DELETE" });

// ─── Analysis ────────────────────────────────────────────────────────────────

export const getStockQuick = (symbol: string) =>
  apiFetch<FullAnalysis>(`/stocks/${encodeURIComponent(symbol)}`);

export interface ChartCandle {
  time: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
  ema20: number | null;
  tema9: number | null;
  bb_upper: number | null;
  bb_middle: number | null;
  bb_lower: number | null;
  rsi: number | null;
  macd_line: number | null;
  macd_signal: number | null;
  macd_hist: number | null;
  zigzag: number | null;
}

export interface ChartData {
  symbol: string;
  period: string;
  interval: string;
  candles: ChartCandle[];
  error?: string;
}

export const getStockChart = (symbol: string, period = "1d", interval = "5m") =>
  apiFetch<ChartData>(`/stocks/${encodeURIComponent(symbol)}/chart?period=${period}&interval=${interval}`);

export const analyzeSymbol = (symbol: string) =>
  apiFetch<FullAnalysis>(`/analyze/${encodeURIComponent(symbol)}`);

export const getAnalysisHistory = (symbol: string) =>
  apiFetch<AnalysisHistoryItem[]>(`/analysis/history/${encodeURIComponent(symbol)}`);

export const getConsensus = (symbol: string) =>
  apiFetch<ConsensusResult>(`/analyze/${encodeURIComponent(symbol)}/consensus`);

export const askWhyDisagree = (symbol: string) =>
  apiFetch<WhyDisagreeResult>(`/analyze/${encodeURIComponent(symbol)}/why-disagree`, { method: "POST" });

export const deleteAnalysisHistory = (symbol: string, id: number) =>
  apiFetch<{ deleted: number }>(
    `/analysis/history/${encodeURIComponent(symbol)}/${id}`,
    { method: "DELETE" }
  );

export const askSecondOpinion = (symbol: string, provider: string, model: string) =>
  apiFetch<FullAnalysis>(`/analyze/${encodeURIComponent(symbol)}/opinion`, {
    method: "POST",
    body: JSON.stringify({ provider, model }),
  });

export const analyzeTechnical = (symbol: string) =>
  apiFetch<TechnicalResult>(`/analyze/${symbol}/technical`);

export const analyzeFundamental = (symbol: string) =>
  apiFetch<FundamentalResult>(`/analyze/${symbol}/fundamental`);

export const analyzeNews = (symbol: string) =>
  apiFetch<NewsResult>(`/analyze/${symbol}/news`);

export const analyzeWatchlist = () =>
  apiFetch<FullAnalysis[]>("/analyze/watchlist", { method: "POST" });

// ─── Optimizer ───────────────────────────────────────────────────────────────

export interface SwapSuggestion {
  sell_symbol: string | null;
  buy_symbol: string | null;
  reason: string;
  score_improvement: number;
  sector: string;
  type: "SELL" | "SWAP" | "REDUCE";
}

export type AllocationAction = "BUY" | "ACCUMULATE" | "HOLD" | "REDUCE" | "SELL" | "WATCH";

export type ExecutionRisk = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type AssetType = "EQUITY" | "DR" | "ETF" | "INDEX";

export interface ExecutionSymbolMetadata {
  asset_type: AssetType;
  liquidity_score: number;
  spread_score: number;
  execution_quality_score: number;
  execution_risk: ExecutionRisk;
  execution_warnings: string[];
  position_cap_pct: number | null;
  slippage_cost_est_pct: number;
  combined_score_penalty: number;
}

export interface ExecutionContext {
  per_symbol: Record<string, ExecutionSymbolMetadata>;
  has_dr_assets: boolean;
  dr_symbols: string[];
  high_risk_symbols: string[];
  dr_position_cap: number;
  dr_portfolio_cap: number;
  execution_summary: string;
}

export interface TargetAllocation {
  symbol: string;
  current_weight: number;
  target_weight: number;
  action: AllocationAction;
  allocation_change_percent: number;
  estimated_amount: number;
  reason: string;
  // Phase 3B.10 — execution quality metadata (attached post-AI)
  execution_risk?: ExecutionRisk;
  execution_warnings?: string[];
  asset_type?: AssetType;
  slippage_est_pct?: number;
  execution_capped?: boolean;
  // Presentation-layer noise filter (micro-rebalance suppression)
  noise_suppressed?: boolean;
  noise_reason?: string;
}

export interface OptimizerLayerConfig {
  name: string;
  role: string;
  provider: string;
  model: string;
}

export interface OptimizerLayers {
  layer1: OptimizerLayerConfig;
  layer2: OptimizerLayerConfig;
  layer3: OptimizerLayerConfig;
}

export interface OptimizerFallback {
  provider: string;
  model: string;
}

export interface RiskFlag {
  symbol: string;
  issue: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
}

export interface Layer1Result {
  target_allocations?: TargetAllocation[];
  target_cash_weight?: number;
  portfolio_turnover_percent?: number;
  summary?: string;
  swap_suggestions?: SwapSuggestion[];
  watchlist_ranking?: WatchlistRanking[];
  reasoning?: string;
  priority?: string;
  portfolio_assessment?: string;
  optimization_notes?: string;
  provider?: string;
  model?: string;
  name?: string;
  error?: string;
}

export interface Layer2Result {
  agrees_with_layer1: boolean;
  disagreements?: string[];
  target_allocations?: TargetAllocation[];
  target_cash_weight?: number;
  portfolio_turnover_percent?: number;
  summary?: string;
  alternative_suggestions?: SwapSuggestion[];
  alternative_allocation?: Record<string, string> | null;
  provider?: string;
  model?: string;
  name?: string;
  error?: string;
}

export interface Layer3Result {
  risk_flags?: RiskFlag[];
  safer_choice?: "layer1" | "layer2" | "neither";
  final_risk_level?: "low" | "medium" | "high";
  auditor_notes?: string;
  provider?: string;
  model?: string;
  name?: string;
  error?: string;
}

export interface SectorWeight {
  value: number;
  weight_pct: number;
}

export interface SectorWarning {
  sector: string;
  current_pct: number;
  projected_pct: number;
  limit_pct: number;
  status: "OK" | "WARNING" | "EXCEEDS";
}

export interface BlockedOpportunity {
  symbol: string;
  signal: string;
  reason: string;
}

export type OptimizerStatus =
  | "REBALANCE"
  | "REBALANCE_REQUIRED"
  | "NO_ACTION"
  | "NO_REBALANCE_REQUIRED"
  | "COOLDOWN_ACTIVE"
  | "OPTIMAL";

export type StabilizationOverrideReason =
  | "REGIME_CHANGE"
  | "SECTOR_CONCENTRATION_BREACH"
  | "SINGLE_POSITION_BREACH"
  | "RISK_POLICY_VIOLATION"
  | "DRAWDOWN_EVENT"
  | "CONFIDENCE_COLLAPSE"
  | "MANUAL_OVERRIDE";

export interface DriftAnalysisItem {
  symbol: string;
  current_weight: number;
  target_weight: number;
  allocation_drift: number;
  within_tolerance: boolean;
}

export interface StabilizationCooldown {
  active: boolean;
  last_rebalance_at: string | null;
  days_elapsed: number;
  days_remaining: number;
  cooldown_days: number;
  overridden: boolean;
  override_reasons: StabilizationOverrideReason[];
}

export interface StabilizationMinimumImpact {
  expected_improvement_pct: number;
  estimated_cost_pct: number;
  net_benefit_pct: number;
  passes_threshold: boolean;
  threshold_pct: number;
  suppressed: boolean;
  total_turnover_pct: number;
}

export interface DuplicateTickerDiagnostic {
  total_duplicates_found: number;
  duplicates: Array<{ symbol: string; count: number; layer: string }>;
  by_layer: Record<string, string[]>;
  root_cause_hypothesis: string | null;
}

export interface StabilizationMeta {
  enabled: boolean;
  status: OptimizerStatus;
  original_optimizer_status: OptimizerStatus;
  reason: string | null;
  drift_threshold_pct: number;
  cooldown_days: number;
  net_benefit_threshold_pct: number;
  positions_within_tolerance: number;
  positions_needing_action: number;
  all_within_tolerance: boolean;
  drift_analysis: DriftAnalysisItem[];
  cooldown: StabilizationCooldown;
  minimum_impact: StabilizationMinimumImpact;
  overrides_active: StabilizationOverrideReason[];
  force_rebalance: boolean;
  duplicate_ticker_diagnostic: DuplicateTickerDiagnostic;
}

export type NoActionReason =
  | "WELL_BALANCED"
  | "LOW_CONFIDENCE"
  | "HIGH_DISAGREEMENT"
  | "CONSTRAINT_BLOCKED"
  | "MARKET_UNCERTAINTY"
  | "INSUFFICIENT_EDGE"
  | "COOLDOWN_ACTIVE";

export type ConsensusType =
  | "STRONG_CONSENSUS"
  | "REFINED_CONSENSUS"
  | "PARTIAL_CONSENSUS"
  | "WEAK_CONSENSUS"
  | "RISK_CONFLICT"
  | "STRATEGIC_CONFLICT"
  | "NO_ACTION_CONSENSUS"
  | "NO_REBALANCE_CONSENSUS";

export interface OptimizerConsensus {
  // New Consensus Strength Matrix fields
  consensus_type?: ConsensusType;
  consensus_strength_score?: number;
  strategist_alignment_score?: number;
  risk_alignment_score?: number;
  disagreement_reasons?: string[];
  refinement_summary?: string | null;
  // Phase 3B.4 — Policy governance scores
  policy_alignment_score?: number | null;
  regime_compliance_score?: number | null;
  risk_governance_score?: number | null;
  governance_flags?: string[];
  violation_details?: PolicyViolationDetail[];
  // Legacy fields (preserved for backward compat with old history rows)
  agrees: boolean;
  consensus_decision?: "REBALANCE" | "REBALANCE_REQUIRED" | "NO_ACTION" | "NO_REBALANCE_REQUIRED" | "COOLDOWN_ACTIVE" | "OPTIMAL" | "REVIEW";
  confidence: "high" | "medium" | "low";
  recommended: "layer1" | "layer2" | "neither" | "no_action" | "fallback";
  final_risk_level: "low" | "medium" | "high";
  risk_flag_count: number;
  recommended_action: string;
}

export interface WatchlistRanking {
  symbol: string;
  rank: number;
  signal: "ACCUMULATE" | "BUY" | "WATCH" | "HOLD" | "REDUCE" | "SELL";
  combined_score: number;
  sector: string;
  suggested_allocation_pct: number;
  reasoning: string;
  upside_pct?: number | null;
}

// ─── Strategy Persona ─────────────────────────────────────────────────────────

export type StrategyPersona = "BALANCED" | "GROWTH" | "VALUE" | "DIVIDEND" | "MOMENTUM" | "PASSIVE";
export type DriftSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type RebalanceUrgency = "LOW" | "MODERATE" | "HIGH" | "CRITICAL";

// ─── Phase 3B.4 — Adaptive Policy Engine ─────────────────────────────────────

export type DeploymentBias = "AGGRESSIVE" | "SELECTIVE" | "DEFENSIVE" | "PRESERVATION";
export type StrictnessLevel = "RELAXED" | "NORMAL" | "STRICT" | "EMERGENCY";

export interface PolicyHardConstraints {
  min_cash_pct: number;
  max_single_position_pct: number;
  max_sector_pct: number;
  max_turnover_pct: number;
  suppress_speculative: boolean;
  beta_ceiling: number | null;
  max_new_positions: number;
}

export interface ActivePolicy {
  hard_constraints: PolicyHardConstraints;
  soft_factor_tilts: Record<string, number>;
  deployment_bias: DeploymentBias;
  risk_budget: number;
  rebalance_aggressiveness: number;
  strictness_level: StrictnessLevel;
  emergency_override: boolean;
  emergency_reason: string | null;
  policy_narrative: string;
  confidence_discount: number;
  violations: string[];
  resolved_sector_limits?: Record<string, number>;
  // Governance scores — populated after constraint enforcement
  policy_alignment_score?: number | null;
  regime_compliance_score?: number | null;
  risk_governance_score?: number | null;
  governance_flags?: string[];
  violation_details?: PolicyViolationDetail[];
  // Phase 3B.6 — Dynamic Tier 1 turnover relaxation
  turnover_relaxation_active?: boolean;
  relaxed_turnover_cap?: number | null;
  turnover_relaxation_reason?: string | null;
}

// ─── Phase 3B.5 — Constraint Resolution Layer ────────────────────────────────

export type ConstraintSource =
  | "USER_PREFERENCE"
  | "REGIME_POLICY"
  | "EMERGENCY_OVERRIDE"
  | "SYSTEM_SAFETY";

export interface ConstraintBreakdown {
  user_pref: number;
  regime_policy: number;
  emergency_limit: number | null;
  system_safety: number;
  effective: number;
  binding_source: ConstraintSource;
  tightened_reason: string | null;
}

export interface EffectiveEnvelope {
  single_position: ConstraintBreakdown;
  cash_min: ConstraintBreakdown;
  turnover_max: ConstraintBreakdown;
  beta_ceiling: number | null;
  sector_limits: Record<string, ConstraintBreakdown>;
  global_sector_cap: ConstraintBreakdown;
  effective_single_position_pct: number;
  effective_cash_min_pct: number;
  effective_turnover_max_pct: number;
  effective_sector_limits: Record<string, number>;
  emergency_active: boolean;
  regime_name: string;
  resolver_notes: string[];
}

export type PolicyViolationType =
  | "SECTOR_LIMIT"
  | "SINGLE_POSITION_LIMIT"
  | "CASH_BREACH"
  | "TURNOVER_BREACH"
  | "TURNOVER_RELAXED"
  | "BETA_EXPOSURE";

export type ConstraintTier =
  | "TIER1_CRITICAL"
  | "TIER2_STRATEGIC"
  | "TIER3_EFFICIENCY";

export interface PolicyViolationDetail {
  violation_type: PolicyViolationType;
  sector?: string;
  symbol?: string;
  proposed_pct: number;
  allowed_pct: number;
  violation_source: ConstraintSource;
  tier?: ConstraintTier;
  base_cap?: number;
}

export interface StrategyProfile {
  id: StrategyPersona;
  label: string;
  description: string;
  factor_weights: Record<string, number>;
  turnover_tolerance: number;
  max_cash_preference: number;
  volatility_tolerance: number;
  sector_concentration_tolerance: number;
  rebalance_aggressiveness: number;
}

export interface PortfolioDNA {
  growth: number;
  value: number;
  momentum: number;
  quality: number;
  dividend: number;
}

export interface OptimizerResult {
  portfolio_name: string;
  status?: OptimizerStatus;
  final_consensus_score?: number | null;
  rebalance_opportunity_score?: number;
  no_action_reason?: NoActionReason | null;
  no_action_summary?: string | null;
  blocked_opportunities?: BlockedOpportunity[];
  portfolio_assessment: string;
  optimization_notes: string;
  target_allocations?: TargetAllocation[];
  target_cash_weight?: number;
  portfolio_turnover_percent?: number;
  swap_suggestions: SwapSuggestion[];
  watchlist_ranking: WatchlistRanking[];
  analyzed_at: string;
  history_id?: number;
  portfolio_count: number;
  max_reached: boolean;
  max_stocks?: number;
  cash_balance?: number;
  total_value?: number;
  ai_provider?: string;
  ai_model?: string;
  layer1_result?: Layer1Result | null;
  layer2_result?: Layer2Result | null;
  layer3_result?: Layer3Result | null;
  consensus?: OptimizerConsensus | null;
  current_sector_weights?: Record<string, SectorWeight>;
  projected_sector_weights?: Record<string, SectorWeight>;
  sector_warnings?: SectorWarning[];
  // Strategy persona & portfolio DNA fields
  target_persona?: StrategyPersona | null;
  persona_label?: string | null;
  current_portfolio_dna?: PortfolioDNA | null;
  style_drift_score?: number | null;
  style_drift_severity?: DriftSeverity | null;
  factor_alignment_score?: number | null;
  factor_drift?: Record<string, number> | null;
  rebalance_urgency?: RebalanceUrgency | null;
  // Market regime context (injected at optimizer run time)
  market_regime?: Pick<
    MarketRegime,
    | "regime"
    | "confidence_pct"
    | "trend_score"
    | "volatility_score"
    | "transition_stability"
    | "regime_duration_days"
    | "narrative"
    | "transition_warnings"
  > | null;
  // Phase 3B.4 — Active Policy Envelope
  active_policy?: ActivePolicy | null;
  // Phase 3B.5 — Resolved constraint breakdown
  effective_envelope?: EffectiveEnvelope | null;
  // Phase 3B.7A — Decision Memory
  recommendation_snapshot_id?: number | null;
  // Phase 3B.10 — DR / execution quality context
  execution_context?: ExecutionContext | null;
  // Stabilization Sprint — post-processing churn reduction layer
  stabilization?: StabilizationMeta | null;
}

export interface OptimizerHistoryItem {
  id: number;
  portfolio_name: string;
  analyzed_at: string;
  swap_count: number;
  optimizer_status?: OptimizerStatus;
  final_consensus_score?: number | null;
  rebalance_opportunity_score?: number | null;
  no_action_reason?: NoActionReason | null;
}

export const runOptimizer = (
  portfolioId: number,
  provider?: string,
  model?: string,
  forceRebalance?: boolean,
) =>
  apiFetch<OptimizerResult>("/analyze/optimizer", {
    method: "POST",
    body: JSON.stringify({
      portfolio_id: portfolioId,
      ...(provider        ? { provider }                       : {}),
      ...(model           ? { model }                          : {}),
      ...(forceRebalance  ? { force_rebalance: true }          : {}),
    }),
  });

export const listOptimizerHistory = (portfolioId: number) =>
  apiFetch<OptimizerHistoryItem[]>(`/optimizer/history?portfolio_id=${portfolioId}`);

export const getOptimizerHistory = (historyId: number) =>
  apiFetch<OptimizerResult>(`/optimizer/history/${historyId}`);

export const listStrategyProfiles = () =>
  apiFetch<{ profiles: StrategyProfile[] }>("/strategy-profiles");

export const getPortfolioPersona = (portfolioId: number) =>
  apiFetch<{ persona: StrategyPersona; profile: StrategyProfile }>(`/portfolios/${portfolioId}/persona`);

export const updatePortfolioPersona = (portfolioId: number, persona: StrategyPersona) =>
  apiFetch<{ persona: StrategyPersona; ok: boolean }>(`/portfolios/${portfolioId}/persona`, {
    method: "PATCH",
    body: JSON.stringify({ persona }),
  });

export interface AnalysisLatencyStat {
  provider: string;
  model: string;
  avg_latency_ms: number;
  min_latency_ms: number;
  max_latency_ms: number;
  p95_latency_ms: number;
  call_count: number;
  last_used: string | null;
}

export interface OptimizerLatencyStat {
  provider: string;
  model: string;
  layer: string;
  avg_latency_ms: number;
  call_count: number;
}

export interface LatencyStats {
  analysis: AnalysisLatencyStat[];
  optimizer: OptimizerLatencyStat[];
}

export interface ModelCostStat {
  model: string;
  provider: string;
  total_input_tokens: number;
  total_output_tokens: number;
  estimated_cost_usd: number;
  estimated_cost_thb?: number;
  call_count: number;
}

export interface CostEstimate {
  fx?: { usd_to_thb: number };
  by_model: ModelCostStat[];
  total_estimated_usd: number;
  total_estimated_thb?: number;
}

function _dateQS(fromDate?: string, toDate?: string): string {
  const p = new URLSearchParams();
  if (fromDate) p.set("from_date", fromDate);
  if (toDate) p.set("to_date", toDate);
  const qs = p.toString();
  return qs ? `?${qs}` : "";
}

export const getLatencyStats = (fromDate?: string, toDate?: string) =>
  apiFetch<LatencyStats>(`/stats/latency${_dateQS(fromDate, toDate)}`);

export const getCostEstimate = (fromDate?: string, toDate?: string) =>
  apiFetch<CostEstimate>(`/stats/cost-estimate${_dateQS(fromDate, toDate)}`);

export interface BackfillSectorsResult {
  watchlist_updated: number;
  portfolio_updated: number;
  failed: string[];
}

export const backfillSectors = () =>
  apiFetch<BackfillSectorsResult>("/admin/backfill-sectors", { method: "POST" });

export const updateSwapPermission = (portfolioId: number, symbol: string, allow_swap: boolean) =>
  apiFetch<{ symbol: string; allow_swap: boolean }>(
    `/portfolios/${portfolioId}/holdings/${encodeURIComponent(symbol)}/swap-permission`,
    { method: "PATCH", body: JSON.stringify({ allow_swap }) }
  );

// ─── AI Models & Settings ─────────────────────────────────────────────────────

export interface AIModelEntry {
  id: string;
  apiModel?: string;
  label: string;
  provider: string;
  memo?: string;
  cost?: { token_1m: { input: number; output: number; caching?: number } };
}

export interface AIModelsConfig {
  default: string;
  providers: Record<string, { baseURL: string; envKey: string }>;
  models: AIModelEntry[];
}

export interface AISettings {
  analyze_provider: string;
  analyze_model: string;
  optimize_provider: string;
  optimize_model: string;
}

export const getAIModels = () => apiFetch<AIModelsConfig>("/ai-models");
export const getAISettings = () => apiFetch<AISettings>("/settings/ai-models");
export const updateAISettings = (body: Partial<AISettings>) =>
  apiFetch<AISettings>("/settings/ai-models", {
    method: "PATCH",
    body: JSON.stringify(body),
  });

export const getAnalysisSources = () => apiFetch<AnalysisSources>("/settings/analysis-sources");

export const updateAnalysisSource = (key: keyof AnalysisSources, value: boolean) =>
  apiFetch<AnalysisSources>("/settings/analysis-sources", {
    method: "PATCH",
    body: JSON.stringify({ [key]: value }),
  });

export interface PortfolioSettings {
  max_stocks: number;
  max_sector_pct: number;
}

export type SectorLimits = Record<string, number>;

export const getSectorLimits = () => apiFetch<SectorLimits>("/settings/sector-limits");
export const updateSectorLimits = (limits: SectorLimits) =>
  apiFetch<SectorLimits>("/settings/sector-limits", {
    method: "PATCH",
    body: JSON.stringify({ limits }),
  });

export const getPortfolioSettings = () => apiFetch<PortfolioSettings>("/settings/portfolio");
export const updatePortfolioSettings = (body: Partial<PortfolioSettings>) =>
  apiFetch<PortfolioSettings>("/settings/portfolio", {
    method: "PATCH",
    body: JSON.stringify(body),
  });

export const getOptimizerLayers = () => apiFetch<OptimizerLayers>("/settings/optimizer-layers");

export const updateOptimizerLayer = (layer: "layer1" | "layer2" | "layer3", provider: string, model: string) =>
  apiFetch<OptimizerLayers>("/settings/optimizer-layers", {
    method: "PATCH",
    body: JSON.stringify({ layer, provider, model }),
  });

export const getOptimizerFallback = () => apiFetch<OptimizerFallback>("/settings/optimizer-fallback");

export const updateOptimizerFallback = (provider: string, model: string) =>
  apiFetch<OptimizerFallback>("/settings/optimizer-fallback", {
    method: "PATCH",
    body: JSON.stringify({ provider, model }),
  });

// ─── Transactions ─────────────────────────────────────────────────────────────

export type TransactionType =
  | "BUY"
  | "SELL"
  | "DEPOSIT"
  | "WITHDRAW"
  | "INITIAL_POSITION"
  | "INITIAL_CASH"
  | "DIVIDEND";

export interface TransactionRecord {
  id: number;
  portfolio_id: number;
  symbol: string | null;
  type: TransactionType;
  shares: number | null;
  price_per_share: number | null;
  total_amount: number;
  fees: number;
  taxes: number;
  currency: string;
  exchange_rate: number;
  transaction_date: string;
  notes: string | null;
  sector: string | null;
  created_at: string | null;
}

export interface TransactionHolding {
  shares: number;
  avg_cost: number;
  sector: string | null;
}

export interface TransactionResult {
  transaction_id: number;
  type: TransactionType;
  symbol: string | null;
  // equity fields (BUY / SELL / INITIAL_POSITION)
  shares?: number;
  price_per_share?: number;
  // cash fields (DEPOSIT / WITHDRAW / INITIAL_CASH)
  amount?: number;
  total_amount: number;
  fees?: number;
  taxes?: number;
  transaction_date: string;
  notes: string | null;
  realized_pnl?: number;
  holding_removed?: boolean;
  cash_balance?: number | null;
  holding: TransactionHolding | null;
}

export interface BuyPayload {
  symbol: string;
  shares: number;
  price_per_share: number;
  currency?: string;
  exchange_rate?: number;
  transaction_date?: string;
  notes?: string;
}

export interface SellPayload {
  symbol: string;
  shares: number;
  price_per_share: number;
  currency?: string;
  exchange_rate?: number;
  transaction_date?: string;
  notes?: string;
  remove_if_zero?: boolean;
}

export interface DepositPayload {
  amount: number;
  currency?: string;
  exchange_rate?: number;
  transaction_date?: string;
  notes?: string;
}

export interface WithdrawPayload {
  amount: number;
  currency?: string;
  exchange_rate?: number;
  transaction_date?: string;
  notes?: string;
}

export interface InitialPositionPayload {
  symbol: string;
  shares: number;
  avg_cost: number;
  transaction_date?: string;
  notes?: string;
}

export interface InitialCashPayload {
  amount: number;
  currency?: string;
  transaction_date?: string;
  notes?: string;
}

export interface DividendPayload {
  symbol?: string;
  amount: number;
  currency?: string;
  exchange_rate?: number;
  transaction_date?: string;
  notes?: string;
}

export const buyTransaction = (portfolioId: number, payload: BuyPayload) =>
  apiFetch<TransactionResult>(`/portfolios/${portfolioId}/transactions/buy`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const sellTransaction = (portfolioId: number, payload: SellPayload) =>
  apiFetch<TransactionResult>(`/portfolios/${portfolioId}/transactions/sell`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const depositTransaction = (portfolioId: number, payload: DepositPayload) =>
  apiFetch<TransactionResult>(`/portfolios/${portfolioId}/transactions/deposit`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const withdrawTransaction = (portfolioId: number, payload: WithdrawPayload) =>
  apiFetch<TransactionResult>(`/portfolios/${portfolioId}/transactions/withdraw`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const initialPositionTransaction = (portfolioId: number, payload: InitialPositionPayload) =>
  apiFetch<TransactionResult>(`/portfolios/${portfolioId}/transactions/initial-position`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const initialCashTransaction = (portfolioId: number, payload: InitialCashPayload) =>
  apiFetch<TransactionResult>(`/portfolios/${portfolioId}/transactions/initial-cash`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const dividendTransaction = (portfolioId: number, payload: DividendPayload) =>
  apiFetch<TransactionResult>(`/portfolios/${portfolioId}/transactions/dividend`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const getTransactionHistory = (portfolioId: number, symbol?: string, limit = 100) => {
  const params = new URLSearchParams({ limit: String(limit) });
  if (symbol) params.set("symbol", symbol);
  return apiFetch<TransactionRecord[]>(`/portfolios/${portfolioId}/transactions?${params}`);
};

export const getLatestSignal = (symbol: string) =>
  apiFetch<{
    symbol: string;
    signal: string | null;
    confidence: string | null;
    reasoning: string | null;
    risks: string | null;
    analyzed_at: string | null;
  }>(`/portfolio/${encodeURIComponent(symbol)}/latest-signal`);

export interface CostUsageRow {
  date?: string;
  provider: string;
  model: string;
  layer?: string | null;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  total_cost_usd: number;
  total_cost_thb: number;
}

export interface ModelCostReport {
  month: string;
  fx: { usd_to_thb: number };
  analyze: {
    month_total_usd: number;
    month_total_thb: number;
    daily: CostUsageRow[];
    by_model_month: CostUsageRow[];
  };
  optimize: {
    month_total_usd: number;
    month_total_thb: number;
    daily: CostUsageRow[];
    by_model_layer_month: CostUsageRow[];
  };
}

export const getModelCostReport = (year?: number, month?: number) => {
  const params = new URLSearchParams();
  if (year) params.set("year", String(year));
  if (month) params.set("month", String(month));
  const qs = params.toString();
  return apiFetch<ModelCostReport>(`/usage/model-cost-report${qs ? `?${qs}` : ""}`);
};

// ─── Factor Exposure Analytics ────────────────────────────────────────────────

export interface FactorDetail {
  score: number | null;
  label: string;
  description: string;
}

export interface StyleClassification {
  primary: string;
  secondary: string | null;
  confidence: "high" | "medium" | "low";
  dominant_factors: string[];
  rationale: string;
}

export interface PerStockFactorScore {
  symbol: string;
  sector: string | null;
  weight: number;
  scores: {
    growth: number | null;
    value: number | null;
    dividend: number | null;
    momentum: number | null;
    quality: number | null;
  };
  data_coverage: number;
}

export interface RawMetricsSummary {
  avg_pe: number | null;
  avg_price_to_book: number | null;
  avg_revenue_growth: number | null;
  avg_earnings_growth: number | null;
  avg_roe: number | null;
  avg_net_margin: number | null;
  avg_debt_equity: number | null;
  avg_dividend_yield: number | null;
  avg_return_30d: number | null;
}

export interface FactorSectorConcentration {
  sector_weights: Record<string, number | null>;  // backend may emit null weights
  top_sector: string | null;
  top_sector_weight: number | null;
  diversification_score: number | null;
  hhi: number | null;
  hhi_label: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | null;
  concentration_flags: string[];
}

export interface FactorExposureMetadata {
  universe_size: number;
  data_quality_flags: string[];
  normalization_method: string;
  computed_at: string;
}

export interface FactorExposureResult {
  portfolio_id: number;
  portfolio_name: string;
  generated_at: string;
  factor_exposures: {
    growth: FactorDetail;
    value: FactorDetail;
    dividend: FactorDetail;
    momentum: FactorDetail;
    quality: FactorDetail;
  };
  style_classification: StyleClassification;
  per_stock_scores: PerStockFactorScore[];
  raw_metrics_summary: RawMetricsSummary;
  sector_concentration: FactorSectorConcentration;
  metadata: FactorExposureMetadata;
  error?: string;
}

export const getFactorExposure = (portfolioId: number) =>
  apiFetch<FactorExposureResult>(`/analytics/factor-exposure?portfolio_id=${portfolioId}`);

// ─── Market Regime ────────────────────────────────────────────────────────────

export type RegimeState =
  | "RISK_ON"
  | "RISK_OFF"
  | "SIDEWAYS"
  | "HIGH_VOLATILITY"
  | "DEFENSIVE_REGIME"
  | "TRANSITION_RISK_ON"
  | "TRANSITION_RISK_OFF";

export type TransitionStability = "STABLE" | "TRANSITIONING" | "VOLATILE";

export interface RegimeConstraints {
  min_cash_pct: number;
  max_single_position_pct: number;
  turnover_multiplier: number;
  momentum_bias: boolean;
  quality_bias: boolean;
  dividend_bias: boolean;
  suppress_speculative: boolean;
  deployment_stance: string;
  mandate: string;
}

export interface RegimeHistoryPoint {
  date: string;
  regime: RegimeState;
  confidence: number;
  trend_score: number;
  volatility_score: number;
}

export interface BenchmarkSignal {
  ema_trend_score: number;
  vol_score: number;
  drawdown_score: number;
  momentum_score: number;
  vol_z_score: number;
  return_20d: number;
  realized_vol_20d: number;
}

export interface MarketRegime {
  regime: RegimeState;
  confidence: number;
  confidence_pct: number;
  trend_score: number;
  volatility_score: number;
  drawdown_score: number;
  momentum_score: number;
  vol_z_score: number;
  ema_alignment: number;
  vix_level: number | null;
  regime_duration_days: number;
  previous_regime: RegimeState | "UNKNOWN";
  transition_stability: TransitionStability;
  transition_warnings: string[];
  benchmark_signals: Record<string, BenchmarkSignal>;
  narrative: string;
  constraints: RegimeConstraints;
  regime_history: RegimeHistoryPoint[];
  detected_at: string;
  detection_ms: number;
  data_error?: boolean;
}

export const getMarketRegime = () =>
  apiFetch<MarketRegime>("/analytics/market-regime");

// ─── System Status ────────────────────────────────────────────────────────────

export interface SystemStatus {
  app_env: "local" | "vps" | string;
  role: string;
  read_only_market_data: boolean;
  scheduler_enabled: boolean;
  live_fetch_enabled: boolean;
  description: string;
}

export const getSystemStatus = () =>
  apiFetch<SystemStatus>("/system/status");

// ─── Portfolio Snapshots ──────────────────────────────────────────────────────

export interface SnapshotHolding {
  symbol: string;
  shares: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  sector: string;
}

export interface PortfolioSnapshotRow {
  id: number;
  portfolio_id: number;
  snapshot_date: string;               // "YYYY-MM-DD"
  total_value: number;
  cash_balance: number;
  total_invested: number;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
  realized_pnl: number | null;
  /** Cash-flow-adjusted daily return. Deposits/withdrawals are stripped out. */
  daily_return_pct: number | null;
  /** Same as daily_return_pct — explicit semantic alias for clarity. */
  investment_return_pct: number | null;
  /** Absolute market gain/loss in currency units (no external cash flows). */
  investment_return_amount: number | null;
  /** Net external cash flow this period (deposits − withdrawals − initial cash). Positive = inflow. */
  net_external_cash_flow: number | null;
  /** Market value of INITIAL_POSITION imports in this period. Excluded from return. */
  imported_asset_value: number | null;
  /** Market value of QUANTITY_CORRECTION adjustments in this period. Excluded from return. */
  manual_adjustment_value: number | null;
  /**
   * Realized P&L from SELL transactions in this snapshot window (informational).
   * Already embedded in investment_return_pct through total_value changes.
   * Tip: if this is much larger than investment_return_amount, most of the gain
   * accumulated over prior periods as unrealized P/L — today's return reflects
   * only the price movement since the previous snapshot.
   */
  period_realized_pnl: number | null;
  /** Dividends received in this snapshot window. Included in investment_return_pct. */
  period_dividend_income: number | null;
  /** Total brokerage fees on trades in this window. Drag already reflected in investment_return_pct. */
  period_fees_paid: number | null;
  holdings_count: number | null;
  sector_breakdown: Record<string, number> | null;  // {sector: weight_pct}
  holdings: SnapshotHolding[] | null;
  created_at: string | null;
}

export interface GenerateSnapshotResult extends PortfolioSnapshotRow {
  equity_value: number;
  updated: boolean;
  /** Gross deposits since previous snapshot. */
  net_deposits: number;
  /** Gross withdrawals since previous snapshot. */
  net_withdrawals: number;
}

export const generateSnapshot = (portfolioId: number, snapshotDate?: string) =>
  apiFetch<GenerateSnapshotResult>("/snapshots/generate", {
    method: "POST",
    body: JSON.stringify({ portfolio_id: portfolioId, snapshot_date: snapshotDate ?? null }),
  });

export const getSnapshots = (portfolioId: number, limit = 365) =>
  apiFetch<PortfolioSnapshotRow[]>(
    `/portfolios/${portfolioId}/snapshots?limit=${limit}`
  );

// ─── Benchmark / performance-comparison ──────────────────────────────────────

export interface BenchmarkSeriesMeta {
  key: string;                       // "portfolio" | "bm_SET" | "bm_QQQ"
  label: string;                     // "Main" | "SET Index" | "QQQ (NASDAQ-100)"
  type: "portfolio" | "benchmark";
  symbol: string | null;
}

/** One date point in the flat recharts-ready array. */
export type PerformanceDataPoint = { date: string } & Record<string, number | null>;

export interface PerformanceComparisonResult {
  base_date: string | null;
  portfolio_name: string;
  series: BenchmarkSeriesMeta[];
  data: PerformanceDataPoint[];
}

export const getPerformanceComparison = (
  portfolioId: number,
  benchmarks = "^SET.BK,QQQ",
) =>
  apiFetch<PerformanceComparisonResult>(
    `/analytics/performance-comparison?portfolio_id=${portfolioId}&benchmarks=${encodeURIComponent(benchmarks)}`,
  );

export const benchmarkBackfill = (
  fromDate = "2026-05-21",
  symbols = "^SET.BK,QQQ",
) =>
  apiFetch<{ results: { symbol: string; status: string; rows: number }[]; total_rows_written: number }>(
    `/admin/benchmark-backfill?from_date=${fromDate}&symbols=${encodeURIComponent(symbols)}`,
    { method: "POST" },
  );

// ─── Analytics / Performance Stats ───────────────────────────────────────────

export interface MaxDrawdown {
  max_drawdown_pct: number;
  peak_date: string | null;
  trough_date: string | null;
  recovery_date: string | null;
  duration_days: number | null;
}

export interface MonthlyReturn {
  month: string;       // "2026-05"
  return_pct: number;
}

export interface MonthlyWinRate {
  win_rate: number;
  wins: number;
  losses: number;
  total_months: number;
  monthly_returns: MonthlyReturn[];
}

export interface PortfolioAnalyticsMetrics {
  cumulative_return_pct: number;
  annualized_return_pct: number;
  volatility_pct: number;
  sharpe_ratio: number;
  max_drawdown: MaxDrawdown;
  monthly_win_rate: MonthlyWinRate;
  snapshot_count: number;
  date_range: { from: string; to: string };
}

export type BenchmarkDataQuality = "INSUFFICIENT" | "LOW" | "MODERATE" | "GOOD";
export type BenchmarkStatisticalConfidence = "UNRELIABLE" | "LOW" | "MODERATE" | "HIGH";

export interface BenchmarkStat {
  symbol: string;
  error?: string;               // set when backend couldn't compute metrics
  alpha: number | null;
  beta: number | null;
  r_squared: number | null;
  correlation: number | null;
  tracking_error_pct: number | null;
  information_ratio: number | null;
  aligned_days?: number;        // absent when error is set and < 5 aligned days
  // Data quality fields (present for aligned_days >= 5)
  data_quality?: BenchmarkDataQuality;
  statistical_confidence?: BenchmarkStatisticalConfidence;
  sample_size?: number;
  warnings?: string[];
}

export interface BenchmarkAnalyticsMetrics {
  benchmarks: BenchmarkStat[];
}

export interface SignalWinRate {
  win_rate: number;
  wins: number;
  losses: number;
  total: number;
  n_days: number;
  details?: Array<{ symbol: string; signal_date: string; action: string; return_pct: number | null; win: boolean }>;
}

export interface SignalAccuracy {
  accuracy: number;
  accurate: number;
  inaccurate: number;
  total: number;
  n_days: number;
}

export interface HoldingReturn {
  avg_return_pct: number;
  median_return_pct: number;
  std_return_pct: number;
  sample_size: number;
}

export interface DecayBucket {
  days: number;
  avg_return_pct: number;
  sample_size: number;
}

export interface SignalDecay {
  buckets: DecayBucket[];
  by_action: Record<string, Record<string, { avg_return_pct: number; sample_size: number }>>;
}

export interface SignalAnalyticsMetrics {
  buy_win_rate: SignalWinRate;
  sell_accuracy: SignalAccuracy;
  average_holding_return: HoldingReturn;
  signal_decay: SignalDecay;
  total_signals: number;
  signals_by_action: Record<string, number>;
}

export interface SectorContributionItem {
  sector: string;
  avg_weight_pct: number;
  contribution_pct: number;
}

export interface ContributorItem {
  symbol: string;
  unrealized_pnl_pct: number;
  unrealized_pnl: number;
  market_value: number;
  sector: string;
}

export interface TopContributorsResult {
  top_contributors: ContributorItem[];
  worst_contributors: ContributorItem[];
  snapshot_date: string;
}

export interface CashUtilization {
  avg_cash_pct: number;
  min_cash_pct: number;
  max_cash_pct: number;
  current_cash_pct: number;
}

export interface ConcentrationRisk {
  hhi: number;
  hhi_label: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  top_holding_weight_pct: number;
}

export interface AllocationAnalyticsMetrics {
  sector_contribution: SectorContributionItem[];
  top_contributors: TopContributorsResult;
  cash_utilization: CashUtilization;
  concentration_risk: ConcentrationRisk;
}

export interface EquityCurvePoint {
  date: string;
  total_value: number;
  cumulative_return_pct: number;
  drawdown_pct: number;
  daily_return_pct: number | null;
}

export interface SectorEvolutionPoint {
  date: string;
  [sector: string]: number | string;
}

export interface PerformanceStatsResult {
  portfolio_id: number;
  portfolio_name: string;
  generated_at: string;
  portfolio_metrics: PortfolioAnalyticsMetrics;
  benchmark_metrics: BenchmarkAnalyticsMetrics;
  signal_metrics: SignalAnalyticsMetrics;
  allocation_metrics: AllocationAnalyticsMetrics;
  equity_curve?: EquityCurvePoint[];
  rolling_returns?: Array<{ date: string; rolling_return_pct: number }>;
  sector_evolution?: SectorEvolutionPoint[];
}

export const getPerformanceStats = (
  portfolioId: number,
  options: {
    benchmark?: string;
    includeEquityCurve?: boolean;
    includeRollingReturns?: boolean;
    includeSectorEvolution?: boolean;
  } = {},
) => {
  const {
    benchmark = "^SET.BK,QQQ",
    includeEquityCurve = true,
    includeRollingReturns = false,
    includeSectorEvolution = true,
  } = options;
  const params = new URLSearchParams({
    portfolio_id: String(portfolioId),
    benchmark,
    include_equity_curve: String(includeEquityCurve),
    include_rolling_returns: String(includeRollingReturns),
    include_sector_evolution: String(includeSectorEvolution),
  });
  return apiFetch<PerformanceStatsResult>(`/analytics/performance-stats?${params}`);
};

// ─── Decision Memory System (Phase 3B.7A) ────────────────────────────────────

export type ExecutionDecisionType =
  | "APPROVED"
  | "REJECTED"
  | "PARTIAL_EXECUTION"
  | "MANUAL_OVERRIDE";

export type ShadowPortfolioType = "STATIC_FROZEN" | "ACTIVE_MODEL";

export interface ExecutionDecision {
  id: number;
  portfolio_id: number;
  recommendation_snapshot_id: number;
  optimizer_history_id: number | null;
  decision: ExecutionDecisionType;
  override_notes: string | null;
  executed_at: string;
  created_at: string | null;
}

export interface ExecutionDecisionDetail extends ExecutionDecision {
  approved_allocations: Array<{ symbol: string; target_weight: number; action: string }> | null;
  rejected_symbols: string[] | null;
  recommendation_snapshot: {
    id: number;
    persona: string | null;
    total_portfolio_value: number | null;
    created_at: string | null;
    regime: Record<string, unknown> | null;
    consensus: Record<string, unknown> | null;
    projected_allocations: Array<{ symbol: string; target_weight: number; action: string }> | null;
  } | null;
}

export interface RecordDecisionPayload {
  portfolio_id: number;
  recommendation_snapshot_id: number;
  decision: ExecutionDecisionType;
  approved_allocations?: Array<{ symbol: string; target_weight: number; action: string }>;
  rejected_symbols?: string[];
  override_notes?: string;
  create_static_shadow?: boolean;
}

export interface RecordDecisionResult {
  decision_id: number;
  decision: ExecutionDecisionType;
  recommendation_snapshot_id: number;
  portfolio_id: number;
  executed_at: string;
  static_shadow?: Record<string, unknown>;
}

export interface RecommendationSnapshotFull {
  id: number;
  optimizer_history_id: number;
  portfolio_id: number;
  persona: string | null;
  total_portfolio_value: number | null;
  regime: Record<string, unknown> | null;
  constraint_envelope: Record<string, unknown> | null;
  active_policy: Record<string, unknown> | null;
  layer1: Record<string, unknown> | null;
  layer2: Record<string, unknown> | null;
  layer3: Record<string, unknown> | null;
  consensus: Record<string, unknown> | null;
  portfolio_dna: Record<string, unknown> | null;
  style_drift: Record<string, unknown> | null;
  projected_allocations: Array<{ symbol: string; target_weight: number; action: string }> | null;
  created_at: string | null;
}

export interface ShadowPortfolioSummary {
  id: number;
  portfolio_id: number;
  shadow_type: ShadowPortfolioType;
  name: string;
  inception_date: string;
  inception_value: number | null;
  current_value: number | null;
  inception_return_pct: number | null;
  is_active: boolean;
  last_valued_at: string | null;
  recommendation_snapshot_id: number | null;
  execution_decision_id: number | null;
  created_at: string | null;
}

export interface ShadowDailySnapshot {
  date: string;
  total_value: number;
  return_pct_since_inception: number | null;
  daily_return_pct: number | null;
  benchmark_return_pct: number | null;
  alpha: number | null;
}

export interface ShadowValuationResult {
  shadow_id: number;
  shadow_type: string;
  snapshot_date: string;
  total_value: number;
  inception_return_pct: number | null;
  daily_return_pct: number | null;
  alpha: number | null;
  benchmark_symbol: string;
  benchmark_return_pct: number | null;
}

export interface ShadowPortfolioPerformance extends ShadowPortfolioSummary {
  today_valuation: ShadowValuationResult;
  history: ShadowDailySnapshot[];
}

export interface AttributionPeriodResult {
  status: string;
  evaluation_period_start: string;
  evaluation_period_end: string;
  portfolio_return: number | null;
  benchmark_return: number | null;
  selection_alpha: number | null;
  allocation_alpha: number | null;
  interaction_effect: number | null;
  total_alpha: number | null;
  breakdown_by_sector: Record<string, unknown>;
  note?: string;
}

export interface AttributionHistoryItem {
  id: number;
  evaluation_period_start: string;
  evaluation_period_end: string;
  portfolio_return: number | null;
  benchmark_return: number | null;
  total_alpha: number | null;
  computed_at: string | null;
}

export interface AttributionResult {
  shadow_id: number;
  current: AttributionPeriodResult;
  history: AttributionHistoryItem[];
}

export interface CalibrationDetail {
  id: number;
  lookback_days: number;
  calibration_score: number | null;
  consensus_strength_calibration: number | null;
  policy_alignment_calibration: number | null;
  regime_confidence_calibration: number | null;
  feedback_context: {
    calibration_period: string;
    lookback_days: number;
    calibration_score: number | null;
    signal_accuracy: Record<string, unknown>;
    regime_stability: Record<string, unknown>;
    policy_compliance: Record<string, unknown>;
    insights: string[];
    recommended_adjustments: Record<string, unknown>;
  } | null;
  computed_at: string | null;
}

export interface CalibrationResponse {
  source: "cached" | "computed";
  calibration: CalibrationDetail;
}

export const recordExecutionDecision = (payload: RecordDecisionPayload) =>
  apiFetch<RecordDecisionResult>("/optimizer/decisions", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const listExecutionDecisions = (
  portfolioId?: number,
  decision?: ExecutionDecisionType,
  limit = 50,
) => {
  const params = new URLSearchParams({ limit: String(limit) });
  if (portfolioId) params.set("portfolio_id", String(portfolioId));
  if (decision) params.set("decision", decision);
  return apiFetch<ExecutionDecision[]>(`/optimizer/decisions?${params}`);
};

export const getExecutionDecision = (decisionId: number) =>
  apiFetch<ExecutionDecisionDetail>(`/optimizer/decisions/${decisionId}`);

export const getRecommendationSnapshot = (snapshotId: number) =>
  apiFetch<RecommendationSnapshotFull>(`/optimizer/snapshots/${snapshotId}`);

export const createShadowPortfolio = (payload: {
  portfolio_id: number;
  shadow_type: ShadowPortfolioType;
  execution_decision_id?: number;
  recommendation_snapshot_id?: number;
}) =>
  apiFetch<{ shadow_id: number; shadow_type: ShadowPortfolioType; action?: string; inception_date?: string }>(
    "/analytics/shadow-portfolios",
    { method: "POST", body: JSON.stringify(payload) },
  );

export const listShadowPortfolios = (
  portfolioId?: number,
  shadowType?: ShadowPortfolioType,
  activeOnly = true,
) => {
  const params = new URLSearchParams({ active_only: String(activeOnly) });
  if (portfolioId) params.set("portfolio_id", String(portfolioId));
  if (shadowType) params.set("shadow_type", shadowType);
  return apiFetch<ShadowPortfolioSummary[]>(`/analytics/shadow-portfolios?${params}`);
};

export const getShadowPortfolioPerformance = (shadowId: number) =>
  apiFetch<ShadowPortfolioPerformance>(`/analytics/shadow-portfolios/${shadowId}/performance`);

export const triggerShadowValuation = (shadowId: number) =>
  apiFetch<ShadowValuationResult>(
    `/analytics/shadow-portfolios/${shadowId}/value`,
    { method: "POST" },
  );

export const getAttribution = (shadowId: number, start?: string, end?: string) => {
  const params = new URLSearchParams();
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  const qs = params.toString();
  return apiFetch<AttributionResult>(`/analytics/attribution/${shadowId}${qs ? `?${qs}` : ""}`);
};

export const getCalibration = (
  portfolioId?: number,
  lookbackDays = 30,
  refresh = false,
) => {
  const params = new URLSearchParams({
    lookback_days: String(lookbackDays),
    refresh: String(refresh),
  });
  if (portfolioId) params.set("portfolio_id", String(portfolioId));
  return apiFetch<CalibrationResponse>(`/analytics/calibration?${params}`);
};

// ── Phase 3B.7B — Attribution Analytics & Human-vs-AI Benchmark Engine ────────

export interface ShadowMetrics {
  shadow_id: number | null;
  return_pct: number | null;
  max_drawdown_pct: number;
  annualized_volatility: number | null;
}

export interface PortfolioMetrics {
  return_pct: number | null;
  max_drawdown_pct: number;
  annualized_volatility: number | null;
  snapshot_count: number;
}

export type AttributionDataStatus =
  | "ok"
  | "no_portfolio_snapshots"
  | "insufficient_portfolio_history"
  | "no_shadows"
  | "shadows_pending_valuation";

export interface PortfolioAttributionResult {
  portfolio_id: number;
  evaluation_window_days: number;
  period_start: string;
  period_end: string;
  status: AttributionDataStatus;
  data_points_available: number;
  required_days_remaining: number;
  has_sufficient_history: boolean;
  actual: PortfolioMetrics;
  static_shadow: ShadowMetrics | null;
  ai_model_shadow: ShadowMetrics | null;
  avoided_drawdown_pct: number | null;
  regret_score: number | null;
  ai_outperformed: boolean | null;
  interpretation: string;
  computed_at: string;
}

export interface ShadowReadinessSummary {
  id: number;
  type: "STATIC_FROZEN" | "ACTIVE_MODEL";
  inception_date: string;
  snapshot_count: number;
  latest_snapshot: string | null;
  last_valued_at: string | null;
}

export interface DataReadinessResponse {
  portfolio_id: number;
  pipeline_health: "ok" | "incomplete";
  blockers: string[];
  counts: {
    portfolio_snapshots: number;
    latest_portfolio_snapshot: string | null;
    recommendation_snapshots: number;
    latest_recommendation_snapshot: string | null;
    execution_decisions: number;
    approved_decisions: number;
    active_shadows: number;
    attribution_records: number;
    regime_snapshots: number;
    benchmark_prices: number;
    calibration_records: number;
  };
  shadows: ShadowReadinessSummary[];
}

export interface AttributionHistoryRecord {
  id: number;
  evaluation_window_days: number | null;
  period_start: string;
  period_end: string;
  actual_return_pct: number | null;
  static_shadow_return_pct: number | null;
  ai_model_return_pct: number | null;
  avoided_drawdown_pct: number | null;
  regret_score: number | null;
  ai_outperformed: boolean | null;
  total_alpha: number | null;
  computed_at: string | null;
}

export interface AttributionSummaryResponse {
  portfolio_id: number;
  current: PortfolioAttributionResult;
  history: AttributionHistoryRecord[];
}

export interface DecisionComparison {
  decision_id: number;
  decision_type: string;
  executed_at: string | null;
  shadow_id: number | null;
  shadow_type: string | null;
  since_date: string;
  actual_return_pct: number | null;
  shadow_return_pct: number | null;
  actual_max_drawdown_pct: number;
  shadow_max_drawdown_pct: number;
  return_delta: number | null;
  ai_better: boolean | null;
  vol_delta: number | null;
  drawdown_delta: number | null;
}

export interface HumanVsAISummary {
  total_decisions: number;
  decisions_with_data: number;
  hit_rate_pct: number | null;
  mean_return_delta: number | null;
  mean_volatility_delta: number | null;
  mean_drawdown_delta: number | null;
  ai_wins: number;
  human_wins: number;
  verdict: string;
}

export interface HumanVsAIResponse {
  portfolio_id: number;
  evaluation_days: number;
  decisions: DecisionComparison[];
  summary: HumanVsAISummary;
  status: string;
}

export interface RegimeStats {
  regime: string;
  label: string;
  color: string;
  trading_days: number;
  avg_daily_return_pct: number;
  total_return_pct: number;
  annualized_volatility: number | null;
  min_daily_return_pct: number;
  max_daily_return_pct: number;
}

export interface RegimeOptimizerStats {
  runs: number;
  rebalance_count: number;
  label: string;
  avg_opportunity_score: number | null;
  rebalance_rate_pct: number | null;
}

export interface RegimeAttributionResponse {
  portfolio_id: number;
  lookback_days: number;
  period_start: string;
  period_end: string;
  regimes: Record<string, RegimeStats>;
  best_regime: string | null;
  worst_regime: string | null;
  total_days: number;
  matched_days: number;
  coverage_pct: number;
  optimizer_by_regime: Record<string, RegimeOptimizerStats>;
  status: string;
}

export interface CalibrationBucket {
  correct: number;
  total: number;
  accuracy_pct: number | null;
  score_range: string;
}

export interface EnhancedCalibrationDetail extends CalibrationDetail {
  signal_accuracy?: {
    total_signals: number;
    evaluated: number;
    symbols_with_price: number;
    directionally_correct: number | null;
    accuracy_pct: number | null;
    buckets: Record<string, CalibrationBucket>;
    note: string;
  };
}

// ── Phase 3B.7B API functions ──────────────────────────────────────────────────

export const getAttributionSummary = (
  portfolioId: number,
  evaluationWindowDays = 30,
) => {
  const params = new URLSearchParams({
    portfolio_id: String(portfolioId),
    evaluation_window_days: String(evaluationWindowDays),
  });
  return apiFetch<AttributionSummaryResponse>(`/analytics/attribution-summary?${params}`);
};

export const getHumanVsAI = (portfolioId: number, evaluationDays = 90) => {
  const params = new URLSearchParams({
    portfolio_id: String(portfolioId),
    evaluation_days: String(evaluationDays),
  });
  return apiFetch<HumanVsAIResponse>(`/analytics/human-vs-ai?${params}`);
};

export const getRegimeAttribution = (portfolioId: number, lookbackDays = 90) => {
  const params = new URLSearchParams({
    portfolio_id: String(portfolioId),
    lookback_days: String(lookbackDays),
  });
  return apiFetch<RegimeAttributionResponse>(`/analytics/regime-attribution?${params}`);
};

export const getConfidenceCalibrationV2 = (
  portfolioId?: number,
  lookbackDays = 30,
  refresh = false,
) => {
  const params = new URLSearchParams({
    lookback_days: String(lookbackDays),
    refresh: String(refresh),
  });
  if (portfolioId) params.set("portfolio_id", String(portfolioId));
  return apiFetch<{ source: "cached" | "computed"; calibration: EnhancedCalibrationDetail }>(
    `/analytics/confidence-calibration?${params}`,
  );
};

export const getDataReadiness = (portfolioId: number) => {
  const params = new URLSearchParams({ portfolio_id: String(portfolioId) });
  return apiFetch<DataReadinessResponse>(`/analytics/data-readiness?${params}`);
};

// ─── Decision Memory Timeline (Phase 3B.7C) ──────────────────────────────────

export interface DecisionMemoryShadowSummary {
  shadow_id: number;
  shadow_type: ShadowPortfolioType;
  name: string;
  inception_date: string;
  inception_value: number | null;
  current_value: number | null;
  inception_return_pct: number | null;
  is_active: boolean;
  last_valued_at: string | null;
}

export interface DecisionMemoryEntry {
  decision_id: number;
  decision: ExecutionDecisionType;
  portfolio_id: number;
  override_notes: string | null;
  executed_at: string;
  recommendation_snapshot: {
    id: number;
    persona: string | null;
    total_portfolio_value: number | null;
    created_at: string | null;
    consensus: {
      consensus_type: string | null;
      consensus_strength_score: number | null;
      consensus_decision: string | null;
    } | null;
    regime: { regime: string | null; confidence_pct: number | null } | null;
  } | null;
  shadows: DecisionMemoryShadowSummary[];
}

export interface ConfidenceHistoryEntry {
  id: number;
  lookback_days: number;
  calibration_score: number | null;
  consensus_strength_calibration: number | null;
  policy_alignment_calibration: number | null;
  regime_confidence_calibration: number | null;
  optimizer_history_id: number | null;
  recommendation_snapshot_id: number | null;
  computed_at: string;
}

export const getDecisionMemoryTimeline = (portfolioId: number, limit = 20) =>
  apiFetch<DecisionMemoryEntry[]>(
    `/analytics/decision-memory?portfolio_id=${portfolioId}&limit=${limit}`,
  );

export const getConfidenceHistory = (limit = 20) =>
  apiFetch<ConfidenceHistoryEntry[]>(`/analytics/confidence-history?limit=${limit}`);

// ─── Phase 3B.7C — Execution Lifecycle ───────────────────────────────────────

export interface ShadowSummaryItem {
  shadow_id: number;
  shadow_type: "STATIC_FROZEN" | "ACTIVE_MODEL";
  name: string;
  inception_date: string;
  inception_value: number | null;
  current_value: number | null;
  inception_return_pct: number | null;
  last_valued_at: string | null;
  latest_alpha: number | null;
  latest_benchmark_return_pct: number | null;
  snapshot_count: number;
}

export interface ShadowPerformanceSummary {
  portfolio_id: number;
  has_shadows: boolean;
  shadows: ShadowSummaryItem[];
  summary: {
    static_frozen: ShadowSummaryItem | null;
    active_model: ShadowSummaryItem | null;
    tracking_since: string | null;
  } | null;
}

export interface AIvsHumanTimelineEntry {
  decision_id: number;
  decision_type: ExecutionDecisionType;
  executed_at: string | null;
  since_date: string;
  shadow_id: number | null;
  shadow_type: ShadowPortfolioType | null;
  shadow_return_pct: number | null;
  actual_return_pct: number | null;
  return_delta: number | null;
  ai_better: boolean | null;
  vol_delta: number | null;
  drawdown_delta: number | null;
}

export interface AIvsHumanTimeline {
  portfolio_id: number;
  evaluation_days: number;
  total_decisions: number;
  timeline: AIvsHumanTimelineEntry[];
  summary: {
    hit_rate_pct: number | null;
    mean_return_delta: number | null;
    ai_wins: number;
    human_wins: number;
    verdict: string;
  } | null;
}

export interface CalibrationHistoryEntry {
  id: number;
  lookback_days: number;
  calibration_score: number | null;
  consensus_strength_calibration: number | null;
  policy_alignment_calibration: number | null;
  regime_confidence_calibration: number | null;
  optimizer_history_id: number | null;
  recommendation_snapshot_id: number | null;
  computed_at: string;
}

/** Portfolio-level aggregate shadow performance */
export const getShadowPerformanceSummary = (portfolioId: number) =>
  apiFetch<ShadowPerformanceSummary>(
    `/analytics/shadow-performance?portfolio_id=${portfolioId}`,
  );

/** Per-decision AI vs human timeline */
export const getAIvsHumanTimeline = (
  portfolioId: number,
  evaluationDays = 90,
  limit = 20,
) =>
  apiFetch<AIvsHumanTimeline>(
    `/analytics/ai-vs-human-timeline?portfolio_id=${portfolioId}&evaluation_days=${evaluationDays}&limit=${limit}`,
  );

/** Historical calibration records for a portfolio */
export const getCalibrationHistory = (portfolioId: number, limit = 20) =>
  apiFetch<CalibrationHistoryEntry[]>(
    `/analytics/calibration-history?portfolio_id=${portfolioId}&limit=${limit}`,
  );

/** Record a decision via the per-snapshot convenience endpoint */
export const recordDecisionBySnapshot = (
  snapshotId: number,
  payload: RecordDecisionPayload,
) =>
  apiFetch<RecordDecisionResult>(
    `/optimizer/${snapshotId}/decision`,
    { method: "POST", body: JSON.stringify(payload) },
  );

// ─── Operations Center (Phase 4C.1) ──────────────────────────────────────────

export type OperationsMode = "MUJI" | "QUANT";

export type StationStatus = "GREEN" | "YELLOW" | "RED";

export interface OperationsStation {
  status: StationStatus;
  label_th: string;
  detail: string;
  detail_th: string;
}

export interface AgentHealth {
  market_data_station: OperationsStation;
  macro_station: OperationsStation;
  risk_desk: OperationsStation;
  quant_corner: OperationsStation;
  portfolio_lab: OperationsStation;
  consensus_room: OperationsStation;
}

export interface MujiAction {
  required: boolean;
  action_th: string;
  severity: "INFO" | "WARN" | "ACTION";
  link: string | null;
}

export interface MujiTranslation {
  headline: string;
  summary: string[];
  action_required: MujiAction;
}

export interface OperationsPortfolioSummary {
  portfolio_value: number | null;
  daily_return_pct: number | null;
  goal_target_value: number | null;
  goal_progress_pct: number | null;
  days_since_last_rebalance: number | null;
  snapshot_date: string | null;
}

export interface OperationsMarket {
  regime: string | null;
  confidence_pct: number | null;
  transition_stability: string | null;
  vix_level: number | null;
  regime_duration_days: number | null;
  risk_level: "low" | "medium" | "high" | null;
  label_th: string;
  description_th: string;
  narrative: string | null;
}

export interface OperationsOptimizer {
  last_run_at: string | null;
  optimizer_status: "REBALANCE" | "NO_ACTION" | null;
  consensus_status: string | null;
  consensus_decision: "NO_ACTION" | "REVIEW" | "REBALANCE" | null;
  consensus_score: number | null;
  final_risk_level: string | null;
  recommendation_summary_th: string;
  recommended_action: string | null;
}

export interface OperationsPolicy {
  strictness_level: string | null;
  violations: string[];
  emergency_override: boolean;
  emergency_reason: string | null;
  deployment_bias: string | null;
  policy_narrative: string | null;
  hard_constraints: Record<string, number | boolean | null>;
}

export interface OperationsCenterStatus {
  generated_at: string;
  portfolio_id: number;
  portfolio_name: string | null;
  mode_capabilities: { modes: OperationsMode[]; default_mode: OperationsMode };
  portfolio_summary: OperationsPortfolioSummary;
  goal_profile: GoalProfile;
  market: OperationsMarket;
  optimizer: OperationsOptimizer;
  policy: OperationsPolicy | null;
  agent_health: AgentHealth;
  muji_translation: MujiTranslation;
}

export interface OptimizerProgressStage {
  key: string;
  label_th: string;
  status: "done" | "active" | "pending";
  started_at: string | null;
}

export interface OptimizerProgress {
  running: boolean;
  stage: string | null;
  ok: boolean | null;
  stages: OptimizerProgressStage[];
  started_at: string | null;
  updated_at: string | null;
}

/** Unified Operations Center status (regime + consensus + station health + MUJI Thai) */
export const getOperationsStatus = (portfolioId: number) =>
  apiFetch<OperationsCenterStatus>(`/operations-center/status?portfolio_id=${portfolioId}`);

/** Live optimizer run progress (poll ~1.5s while a run is active) */
export const getOptimizerProgress = (portfolioId: number) =>
  apiFetch<OptimizerProgress>(`/operations-center/optimizer-progress?portfolio_id=${portfolioId}`);

// ─── Phase 4C.4 — Human Idea Intake / AI Committee Review ────────────────────

export interface IdeaReview {
  symbol: string;
  sector: string | null;
  data_available: boolean;
  existing_signal: "ACCUMULATE" | "BUY" | "WATCH" | "HOLD" | "REDUCE" | "SELL" | null;
  signal_confidence: number | null;
  existing_position: boolean;
  current_allocation_pct: number;
  position_limit_pct: number;
  sector_current_pct: number;
  sector_limit_pct: number;
  strategic_fit_score: number;
  strategic_fit_label: "STRONG" | "MODERATE" | "WEAK";
  risk_impact: "LOW" | "MEDIUM" | "HIGH";
  policy_check: "PASS" | "WARNING" | "FAIL";
  committee_decision: "APPROVE" | "WATCH" | "REVIEW" | "DECLINE";
  reason: string;
  optimizer_alignment: "ALIGNED" | "CONTRADICTING" | "NEUTRAL";
  optimizer_action: string | null;
  target_allocation_pct: number | null;
  portfolio_priority: "HIGH" | "MEDIUM" | "LOW";
  warnings: string[];
}

export interface IdeaReviewPortfolioContext {
  portfolio_id: number;
  portfolio_name: string;
  persona: string;
  regime: string | null;
  emergency_active: boolean;
  total_value: number;
  last_optimizer_run_at: string | null;
  generated_at: string;
}

export interface IdeaReviewResponse {
  portfolio_context: IdeaReviewPortfolioContext;
  reviews: IdeaReview[];
  error?: string;
}

export const reviewIdeas = (portfolioId: number, symbols: string[]) =>
  apiFetch<IdeaReviewResponse>(`/portfolios/${portfolioId}/idea-review`, {
    method: "POST",
    body: JSON.stringify({ symbols }),
  });

// ── Phase 4C.5A — Basket Simulation ──────────────────────────────────────────

export interface BasketImpact {
  sector: string;
  before_pct: number;
  after_pct: number;
  delta_pct: number;
  sector_limit_pct: number;
  status: "PASS" | "WARNING" | "FAIL";
}

export interface BasketSimulationResult {
  portfolio_id: number;
  symbols: string[];
  allocation_pct: number;
  total_capital_required_pct: number;
  cash_before_pct: number;
  cash_after_pct: number;
  impacts: BasketImpact[];
  warnings: string[];
  overall_status: "PASS" | "WARNING" | "FAIL";
  error?: string;
}

export const simulateBasket = (
  portfolioId: number,
  symbols: string[],
  allocation_pct: number,
) =>
  apiFetch<BasketSimulationResult>(`/portfolios/${portfolioId}/basket-simulation`, {
    method: "POST",
    body: JSON.stringify({ symbols, allocation_pct }),
  });

export interface SuggestedBasketAllocation {
  symbol: string;
  suggested_pct: number;
}

export interface PortfolioConstructionResult {
  overall_status: "PASS" | "WARNING" | "FAIL";
  recommended_allocation_pct: number;
  total_deployment_pct: number;
  cash_after_pct: number;
  allocations: SuggestedBasketAllocation[];
  reasoning: string[];
  simulation: BasketSimulationResult;
  error?: string;
}

export const suggestAllocation = (portfolioId: number, symbols: string[]) =>
  apiFetch<PortfolioConstructionResult>(
    `/portfolios/${portfolioId}/portfolio-construction`,
    {
      method: "POST",
      body: JSON.stringify({ symbols }),
    },
  );

export interface ScoreBreakdown {
  signal_points: number;
  confidence_points: number;
  fit_points: number;
  priority_points: number;
}

export interface PositionSuggestion {
  symbol: string;
  position_score: number;
  suggested_pct: number;
  signal: string;
  confidence: number;
  breakdown: ScoreBreakdown;
}

export interface PositionSizingResult {
  deployable_cash_pct: number;
  total_allocated_pct: number;
  status: "PASS" | "WARNING" | "FAIL";
  suggestions: PositionSuggestion[];
  reasoning: string[];
  error?: string;
}

export const suggestPositionSizes = (portfolioId: number, symbols: string[]) =>
  apiFetch<PositionSizingResult>(`/portfolios/${portfolioId}/position-sizing`, {
    method: "POST",
    body: JSON.stringify({ symbols }),
  });
