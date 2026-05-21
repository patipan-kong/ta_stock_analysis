import { getToken, logout } from "@/lib/auth";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...init,
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
  created_at: string;
}

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
  signal_counts: { BUY: number; HOLD: number; SELL: number };
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
  type: "SELL" | "SWAP";
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

export interface RiskFlag {
  symbol: string;
  issue: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
}

export interface Layer1Result {
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

export interface OptimizerConsensus {
  agrees: boolean;
  confidence: "high" | "medium" | "low";
  recommended: "layer1" | "layer2" | "neither";
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

export interface OptimizerResult {
  portfolio_name: string;
  portfolio_assessment: string;
  optimization_notes: string;
  swap_suggestions: SwapSuggestion[];
  watchlist_ranking: WatchlistRanking[];
  analyzed_at: string;
  history_id?: number;
  portfolio_count: number;
  max_reached: boolean;
  ai_provider?: string;
  ai_model?: string;
  layer1_result?: Layer1Result | null;
  layer2_result?: Layer2Result | null;
  layer3_result?: Layer3Result | null;
  consensus?: OptimizerConsensus | null;
  current_sector_weights?: Record<string, SectorWeight>;
  projected_sector_weights?: Record<string, SectorWeight>;
  sector_warnings?: SectorWarning[];
}

export interface OptimizerHistoryItem {
  id: number;
  portfolio_name: string;
  analyzed_at: string;
  swap_count: number;
}

export const runOptimizer = (portfolioId: number, provider?: string, model?: string) =>
  apiFetch<OptimizerResult>("/analyze/optimizer", {
    method: "POST",
    body: JSON.stringify({
      portfolio_id: portfolioId,
      ...(provider ? { provider } : {}),
      ...(model    ? { model }    : {}),
    }),
  });

export const listOptimizerHistory = (portfolioId: number) =>
  apiFetch<OptimizerHistoryItem[]>(`/optimizer/history?portfolio_id=${portfolioId}`);

export const getOptimizerHistory = (historyId: number) =>
  apiFetch<OptimizerResult>(`/optimizer/history/${historyId}`);

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
  call_count: number;
}

export interface CostEstimate {
  by_model: ModelCostStat[];
  total_estimated_usd: number;
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

// ─── Transactions ─────────────────────────────────────────────────────────────

export type TransactionType =
  | "BUY"
  | "SELL"
  | "DEPOSIT"
  | "WITHDRAW"
  | "INITIAL_POSITION"
  | "INITIAL_CASH";

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
  fees?: number;
  taxes?: number;
  currency?: string;
  exchange_rate?: number;
  transaction_date?: string;
  notes?: string;
}

export interface SellPayload {
  symbol: string;
  shares: number;
  price_per_share: number;
  fees?: number;
  taxes?: number;
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
  snapshot_date: string;           // "YYYY-MM-DD"
  total_value: number;
  cash_balance: number;
  total_invested: number;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
  realized_pnl: number | null;
  daily_return_pct: number | null;
  holdings_count: number | null;
  sector_breakdown: Record<string, number> | null;  // {sector: weight_pct}
  holdings: SnapshotHolding[] | null;
  created_at: string | null;
}

export interface GenerateSnapshotResult extends PortfolioSnapshotRow {
  equity_value: number;
  updated: boolean;
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
