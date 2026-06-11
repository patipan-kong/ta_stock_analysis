"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import BackBreadcrumb from "@/components/BackBreadcrumb";
import dynamic from "next/dynamic";
import {
  getStockQuick, analyzeSymbol, getAnalysisHistory,
  deleteAnalysisHistory, askSecondOpinion, getAIModels, getAISettings,
} from "@/lib/api";
import SignalBadge from "@/components/SignalBadge";
import AIBadge from "@/components/AIBadge";
import type { FullAnalysis, TimeframeTA, AnalysisHistoryItem, AIModelsConfig, SourcesUsed } from "@/lib/api";
import ConsensusCard from "@/components/ConsensusCard";

const StockChart = dynamic(() => import("@/components/StockChart"), {
  ssr: false,
  loading: () => <div className="h-[340px] animate-pulse bg-gray-100 rounded-xl" />,
});

const TZ = "Asia/Bangkok";

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return (
    d.toLocaleDateString("th-TH", { day: "2-digit", month: "short", year: "2-digit", timeZone: TZ }) +
    " " +
    d.toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit", timeZone: TZ })
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2 text-sm">
      <dt className="font-medium text-gray-500 w-32 shrink-0">{label}</dt>
      <dd className="text-gray-800">{value}</dd>
    </div>
  );
}

function ScorePill({ score }: { score: number }) {
  const cls = score > 0 ? "text-green-600" : score < 0 ? "text-red-600" : "text-gray-500";
  return <span className={`text-xs font-bold ${cls}`}>{score > 0 ? "+" : ""}{score}</span>;
}

function TimeframeCard({ label, frame }: { label: string; frame: TimeframeTA | undefined }) {
  if (!frame) return null;
  const hasError = "error" in frame;
  return (
    <div className="border rounded-lg p-3 bg-gray-50">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{label}</p>
        {!hasError && <ScorePill score={frame.score} />}
      </div>
      {hasError ? (
        <p className="text-xs text-red-400">{frame.error}</p>
      ) : (
        <dl className="space-y-1">
          <Row label="RSI" value={frame.rsi?.toString() ?? "—"} />
          {frame.macd_signal !== "neutral" && <Row label="MACD" value={frame.macd_signal} />}
          <Row label="BB" value={frame.bb_position} />
          <Row label="Trend" value={frame.trend} />
          <Row label="Notes" value={frame.summary} />
        </dl>
      )}
    </div>
  );
}

// ─── Provider badge config (shared with second-opinion panel) ─────────────────

const PROVIDER_BTN: Record<string, { label: string; active: string; idle: string }> = {
  anthropic: { label: "Anthropic", active: "border-orange-400 bg-orange-50 text-orange-700 font-semibold", idle: "border-gray-200 hover:border-gray-300 text-gray-600" },
  openai:    { label: "OpenAI",    active: "border-green-400 bg-green-50 text-green-700 font-semibold",  idle: "border-gray-200 hover:border-gray-300 text-gray-600" },
  gemini:    { label: "Gemini",    active: "border-blue-400 bg-blue-50 text-blue-700 font-semibold",     idle: "border-gray-200 hover:border-gray-300 text-gray-600" },
  deepseek:  { label: "DeepSeek", active: "border-purple-400 bg-purple-50 text-purple-700 font-semibold",idle: "border-gray-200 hover:border-gray-300 text-gray-600" },
  zhipu:     { label: "ZhiPu",    active: "border-gray-400 bg-gray-100 text-gray-700 font-semibold",    idle: "border-gray-200 hover:border-gray-300 text-gray-600" },
  groq:      { label: "Groq",     active: "border-yellow-400 bg-yellow-50 text-yellow-700 font-semibold",idle: "border-gray-200 hover:border-gray-300 text-gray-600" },
};

// ─── Source Badges ───────────────────────────────────────────────────────────

function SourceBadges({ sources }: { sources: SourcesUsed | null | undefined }) {
  if (!sources) return null;
  const pills = [
    { key: "ta",   label: "TA",   on: sources.ta },
    { key: "fa",   label: "FA",   on: sources.fa },
    { key: "news", label: "News", on: sources.news },
  ].filter((p) => p.on);
  if (pills.length === 0) return null;
  return (
    <div className="flex gap-1 flex-wrap">
      {pills.map((p) => (
        <span key={p.key} className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded">
          {p.label}
        </span>
      ))}
    </div>
  );
}

// ─── Second Opinion Panel ─────────────────────────────────────────────────────

function SecondOpinionPanel({
  config, provider, model,
  defaultProvider, defaultModel,
  onProviderChange, onModelChange, onReset,
  onRun, onClose, loading,
}: {
  config: AIModelsConfig;
  provider: string;
  model: string;
  defaultProvider: string;
  defaultModel: string;
  onProviderChange: (p: string) => void;
  onModelChange: (m: string) => void;
  onReset: () => void;
  onRun: () => void;
  onClose: () => void;
  loading: boolean;
}) {
  const providers = [...new Set(config.models.map((m) => m.provider))];
  const filteredModels = config.models.filter((m) => m.provider === provider);
  const isDefault = provider === defaultProvider && model === defaultModel;

  return (
    <div className="absolute right-0 top-10 z-20 bg-white border rounded-xl shadow-lg p-4 w-72">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-semibold text-gray-800">Ask Second Opinion</p>
        {!isDefault && (
          <button
            onClick={onReset}
            className="text-xs text-blue-500 hover:underline"
            title="Revert to settings default"
          >
            ↺ Use default
          </button>
        )}
      </div>

      <div className="mb-3">
        <p className="text-xs text-gray-500 mb-1.5">Provider</p>
        <div className="flex flex-wrap gap-1.5">
          {providers.map((p) => {
            const b = PROVIDER_BTN[p] ?? { label: p, active: "border-blue-400 bg-blue-50 text-blue-700 font-semibold", idle: "border-gray-200 hover:border-gray-300 text-gray-600" };
            return (
              <button
                key={p}
                onClick={() => {
                  onProviderChange(p);
                  const first = config.models.find((m) => m.provider === p);
                  if (first) onModelChange(first.apiModel ?? first.id);
                }}
                className={`text-xs px-2.5 py-1 rounded-lg border transition-colors ${provider === p ? b.active : b.idle}`}
              >
                {b.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="mb-4">
        <p className="text-xs text-gray-500 mb-1.5">Model</p>
        <select
          value={model}
          onChange={(e) => onModelChange(e.target.value)}
          className="w-full border rounded-lg px-2.5 py-1.5 text-sm bg-white"
        >
          {filteredModels.map((m) => {
            const val = m.apiModel ?? m.id;
            const isThisDefault = provider === defaultProvider && val === defaultModel;
            return (
              <option key={m.id} value={val}>
                {m.label}{isThisDefault ? " (default)" : ""}
              </option>
            );
          })}
        </select>
        {isDefault && (
          <p className="text-xs text-gray-400 mt-1 italic">settings default</p>
        )}
      </div>

      <div className="flex gap-2">
        <button
          onClick={onRun}
          disabled={loading}
          className="flex-1 bg-blue-600 text-white text-sm rounded-lg py-1.5 hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Running…" : "Run Analysis"}
        </button>
        <button onClick={onClose} className="text-sm text-gray-400 hover:text-gray-600 px-3">
          Cancel
        </button>
      </div>
    </div>
  );
}

// ─── History Card ─────────────────────────────────────────────────────────────

const SIGNAL_CLS: Record<string, string> = {
  BUY:  "text-green-700 bg-green-50 border-green-200",
  HOLD: "text-amber-700 bg-amber-50 border-amber-200",
  SELL: "text-red-700 bg-red-50 border-red-200",
};
const CONF_CLS: Record<string, string> = {
  high: "text-green-600", medium: "text-amber-600", low: "text-gray-400",
};

function HistoryCard({
  item, isConflict, expanded, onToggle, onDelete, deleting,
}: {
  item: AnalysisHistoryItem;
  isConflict: boolean;
  expanded: boolean;
  onToggle: () => void;
  onDelete: () => void;
  deleting: boolean;
}) {
  return (
    <div className={`border rounded-lg overflow-hidden ${isConflict ? "border-amber-300" : "border-gray-100"}`}>
      {/* Header row — always visible */}
      <div
        className={`flex items-center gap-2 px-3 py-2.5 cursor-pointer hover:bg-gray-50 transition-colors ${isConflict ? "bg-amber-50/40" : "bg-white"}`}
        onClick={onToggle}
      >
        <span className="text-xs text-gray-400 shrink-0 w-28">{formatDate(item.analyzed_at)}</span>
        <AIBadge provider={item.ai_provider} model={item.ai_model} label="" />
        <span className={`text-xs font-semibold px-1.5 py-0.5 rounded border ${SIGNAL_CLS[item.signal] ?? ""}`}>
          {item.signal}
        </span>
        <span className={`text-xs ${CONF_CLS[item.confidence] ?? "text-gray-400"}`}>{item.confidence}</span>
        <SourceBadges sources={item.sources_used} />
        {isConflict && (
          <span className="text-xs text-amber-600 font-medium whitespace-nowrap">⚠ Conflicts</span>
        )}
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          disabled={deleting}
          className="ml-auto text-gray-300 hover:text-red-400 disabled:opacity-30 transition-colors text-base leading-none"
          title="Delete"
        >
          {deleting ? "…" : "🗑"}
        </button>
        <span className="text-gray-300 text-xs ml-1">{expanded ? "▲" : "▼"}</span>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-4 pb-4 pt-3 border-t bg-white space-y-2 text-sm">
          <p className="text-gray-700 leading-relaxed">{item.reasoning}</p>
          <p className="text-xs text-gray-500">
            <span className="font-medium">Risks: </span>{item.risks}
          </p>
          {(item.ta_score != null || item.fa_score != null) && (
            <p className="text-xs text-gray-400">
              {item.ta_score != null && `TA: ${item.ta_score > 0 ? "+" : ""}${item.ta_score}`}
              {item.ta_score != null && item.fa_score != null && " · "}
              {item.fa_score != null && `FA: ${item.fa_score > 0 ? "+" : ""}${item.fa_score}`}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function StockDetailPage() {
  const params = useParams();
  const rawSymbol = decodeURIComponent(params.symbol as string).toUpperCase();
  const isThai = rawSymbol.endsWith(".BK");
  const displaySymbol = rawSymbol.replace(".BK", "");

  // Main analysis
  const [data, setData] = useState<FullAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState("");
  const [reanalyzing, setReanalyzing] = useState(false);

  // History
  const [history, setHistory] = useState<AnalysisHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [lastOpinionId, setLastOpinionId] = useState<number | null>(null);

  // Consensus refresh key
  const [consensusKey, setConsensusKey] = useState(0);

  // Second opinion
  const [opinionOpen, setOpinionOpen] = useState(false);
  const [opinionLoading, setOpinionLoading] = useState(false);
  const [aiConfig, setAiConfig] = useState<AIModelsConfig | null>(null);
  const [defaultOpinionProvider, setDefaultOpinionProvider] = useState("anthropic");
  const [defaultOpinionModel, setDefaultOpinionModel] = useState("claude-sonnet-4-6");
  const [opinionProvider, setOpinionProvider] = useState("anthropic");
  const [opinionModel, setOpinionModel] = useState("claude-sonnet-4-6");

  useEffect(() => {
    getStockQuick(rawSymbol)
      .then(setData)
      .catch((err: Error) => setFetchError(err.message))
      .finally(() => setLoading(false));

    Promise.all([getAIModels(), getAISettings()]).then(([cfg, settings]) => {
      setAiConfig(cfg);
      const p = settings.analyze_provider;
      const m = settings.analyze_model;
      setDefaultOpinionProvider(p);
      setDefaultOpinionModel(m);
      setOpinionProvider(p);
      setOpinionModel(m);
    }).catch(() => {});
  }, [rawSymbol]);

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const h = await getAnalysisHistory(rawSymbol);
      setHistory(h);
      if (h.length > 0) setHistoryOpen(true);
    } catch {
      // history is supplementary — fail silently
    } finally {
      setHistoryLoading(false);
    }
  }, [rawSymbol]);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  async function handleReanalyze() {
    setReanalyzing(true);
    try {
      const result = await analyzeSymbol(rawSymbol);
      setData(result);
      setLastOpinionId(null);
      await loadHistory();
      setConsensusKey((k) => k + 1);
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setReanalyzing(false);
    }
  }

  async function handleDelete(id: number) {
    setDeletingId(id);
    try {
      await deleteAnalysisHistory(rawSymbol, id);
      setHistory((prev) => prev.filter((h) => h.id !== id));
      if (id === lastOpinionId) setLastOpinionId(null);
    } catch {
      // silent
    } finally {
      setDeletingId(null);
    }
  }

  async function handleSecondOpinion() {
    setOpinionLoading(true);
    try {
      await askSecondOpinion(rawSymbol, opinionProvider, opinionModel);
      const h = await getAnalysisHistory(rawSymbol);
      setHistory(h);
      if (h.length > 0) {
        const newest = h[0];
        setLastOpinionId(newest.id);
        setExpandedIds((prev) => new Set([...prev, newest.id]));
        setHistoryOpen(true);
      }
      setOpinionOpen(false);
      setConsensusKey((k) => k + 1);
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : "Second opinion failed");
    } finally {
      setOpinionLoading(false);
    }
  }

  function toggleExpand(id: number) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 w-48 bg-gray-100 rounded" />
        <div className="h-28 bg-gray-100 rounded-xl" />
        <div className="grid grid-cols-2 gap-4">
          <div className="h-48 bg-gray-100 rounded-xl" />
          <div className="h-48 bg-gray-100 rounded-xl" />
        </div>
      </div>
    );
  }

  if (fetchError || !data) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">{displaySymbol}</h1>
        <p className="text-red-500">{fetchError || "No data returned."}</p>
      </div>
    );
  }

  const { technical: tech, fundamental: fund, news, summary } = data;
  const currentSignal = summary && !("error" in summary) ? summary.signal : null;

  return (
    <div className="space-y-6">

      {/* ── Back breadcrumb ── */}
      <BackBreadcrumb parent="กลับ" current={displaySymbol} />

      {/* ── Header ── */}
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold">
          {displaySymbol}
          {isThai && <span className="ml-1 text-sm text-gray-400">.BK (SET)</span>}
        </h1>
        {summary && !("error" in summary) && <SignalBadge signal={summary.signal} />}

        <div className="ml-auto flex items-center gap-2 flex-wrap justify-end">
          {summary?.analyzed_at && (
            <span className="text-xs text-gray-400">
              {summary.from_cache ? "Cached: " : "Analyzed: "}
              {formatDate(summary.analyzed_at)}
            </span>
          )}
          <button
            onClick={handleReanalyze}
            disabled={reanalyzing}
            className="text-sm border rounded-lg px-3 py-1.5 hover:bg-gray-50 disabled:opacity-50 font-medium"
          >
            {reanalyzing ? "Analyzing…" : "Re-analyze"}
          </button>

          {/* Second Opinion button + dropdown panel */}
          {aiConfig && (
            <div className="relative">
              <button
                onClick={() => setOpinionOpen((o) => !o)}
                disabled={opinionLoading}
                className="text-sm border border-blue-200 text-blue-600 rounded-lg px-3 py-1.5 hover:bg-blue-50 disabled:opacity-50 font-medium"
              >
                {opinionLoading ? "Running…" : "Second Opinion"}
              </button>
              {opinionOpen && (
                <SecondOpinionPanel
                  config={aiConfig}
                  provider={opinionProvider}
                  model={opinionModel}
                  defaultProvider={defaultOpinionProvider}
                  defaultModel={defaultOpinionModel}
                  onProviderChange={setOpinionProvider}
                  onModelChange={setOpinionModel}
                  onReset={() => { setOpinionProvider(defaultOpinionProvider); setOpinionModel(defaultOpinionModel); }}
                  onRun={handleSecondOpinion}
                  onClose={() => setOpinionOpen(false)}
                  loading={opinionLoading}
                />
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Executive Summary (plain-Thai qualitative context) ── */}
      {summary && !("error" in summary) && summary.executive_summary && (
        <section className="bg-white border rounded-xl p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            <h2 className="text-lg font-semibold">บทสรุปผู้บริหาร</h2>
            <span className="text-xs text-gray-400 ml-auto">มุมมองเชิงคุณภาพ — ไม่ใช่คำแนะนำการลงทุน</span>
          </div>
          <div className="space-y-3">
            {summary.executive_summary.split(/\n\n+/).map((para, i) => (
              <p key={i} className="text-sm text-gray-800 leading-relaxed">{para.trim()}</p>
            ))}
          </div>
        </section>
      )}

      {/* ── AI Summary ── */}
      {summary && !("error" in summary) ? (
        <section className="bg-white border rounded-xl p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h2 className="text-lg font-semibold">AI Summary</h2>
            {summary.from_cache && (
              <span className="text-xs bg-amber-50 border border-amber-200 text-amber-700 px-2 py-0.5 rounded-full">
                cached
              </span>
            )}
            <span className="text-xs text-gray-400 ml-auto">Confidence: {summary.confidence}</span>
            <AIBadge provider={summary.ai_provider} model={summary.ai_model} />
          </div>
          <div className="mb-3">
            <SourceBadges sources={data.sources_used} />
          </div>
          {summary.ai_summary ? (
            <div className="space-y-3">
              {summary.ai_summary.split(/\n\n+/).map((para, i) => (
                <p key={i} className="text-sm text-gray-800 leading-relaxed">{para.trim()}</p>
              ))}
            </div>
          ) : (
            <>
              {/* legacy cached analyses (pre-interpreter) fall back to reasoning/risks */}
              <p className="text-sm text-gray-800 mb-2">{summary.reasoning}</p>
              <p className="text-xs text-gray-500">
                <span className="font-medium">Risks: </span>{summary.risks}
              </p>
            </>
          )}
        </section>
      ) : (
        <section className="bg-white border border-dashed rounded-xl p-5">
          <p className="text-sm text-gray-500">
            No AI analysis cached yet.{" "}
            <button onClick={handleReanalyze} disabled={reanalyzing}
              className="text-blue-500 hover:underline disabled:opacity-50">
              {reanalyzing ? "Analyzing…" : "Run analysis"}
            </button>
          </p>
        </section>
      )}

      {/* ── Consensus ── */}
      <ConsensusCard symbol={rawSymbol} refreshKey={consensusKey} />

      {/* ── Intraday Chart ── */}
      <section className="bg-white border rounded-xl p-5 shadow-sm">
        <h2 className="text-lg font-semibold mb-3">Price Chart</h2>
        <StockChart symbol={rawSymbol} />
      </section>

      {/* ── Analysis History ── */}
      {(!historyLoading || history.length > 0) && history.length > 0 && (
        <section className="bg-white border rounded-xl shadow-sm overflow-hidden">
          <button
            onClick={() => setHistoryOpen((o) => !o)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50 transition-colors"
          >
            <span className="font-semibold text-gray-800 text-sm">
              Analysis History
              <span className="ml-2 text-xs text-gray-400 font-normal">{history.length} records</span>
            </span>
            <span className="text-gray-400 text-xs">{historyOpen ? "▲" : "▼"}</span>
          </button>

          {historyOpen && (
            <div className="px-4 pb-4 space-y-2 border-t pt-3">
              {history.map((item) => (
                <HistoryCard
                  key={item.id}
                  item={item}
                  isConflict={
                    item.id === lastOpinionId &&
                    currentSignal != null &&
                    item.signal !== currentSignal
                  }
                  expanded={expandedIds.has(item.id)}
                  onToggle={() => toggleExpand(item.id)}
                  onDelete={() => handleDelete(item.id)}
                  deleting={deletingId === item.id}
                />
              ))}
            </div>
          )}
        </section>
      )}

      {/* ── Technical Analysis ── */}
      <section className="bg-white border rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Technical Analysis</h2>
          {tech && !("error" in tech) && "ta_score" in tech && (
            <span className="text-sm text-gray-500">
              Composite: <ScorePill score={tech.ta_score} />
            </span>
          )}
        </div>
        {!tech ? (
          <p className="text-sm text-gray-400">No technical data.</p>
        ) : "error" in tech ? (
          <p className="text-red-400 text-sm">{(tech as { error: string }).error}</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <TimeframeCard label="Short-term · 1mo daily" frame={tech.short_term} />
            <TimeframeCard label="Long-term · 1y weekly" frame={tech.long_term} />
          </div>
        )}
      </section>

      {/* ── Fundamental Analysis ── */}
      <section className="bg-white border rounded-xl p-5 shadow-sm">
        <h2 className="text-lg font-semibold mb-3">Fundamental Analysis</h2>
        {!fund ? (
          <p className="text-sm text-gray-400">No fundamental data.</p>
        ) : "error" in fund ? (
          <p className="text-red-400 text-sm">{(fund as { error: string }).error}</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-1">
            <dl className="space-y-1">
              <Row label="P/E Ratio" value={fund.pe_ratio?.toString() ?? "—"} />
              <Row label="EPS" value={fund.eps?.toString() ?? "—"} />
              <Row label="Revenue Growth" value={fund.revenue_growth != null ? `${(fund.revenue_growth * 100).toFixed(1)}%` : "—"} />
            </dl>
            <dl className="space-y-1">
              <Row label="ROE" value={fund.roe != null ? `${(fund.roe * 100).toFixed(1)}%` : "—"} />
              <Row label="Debt/Equity" value={fund.debt_equity?.toString() ?? "—"} />
              <Row label="FA Score" value={`${fund.fa_score > 0 ? "+" : ""}${fund.fa_score}`} />
            </dl>
            {fund.fa_summary && (
              <p className="col-span-2 text-xs text-gray-500 mt-1">{fund.fa_summary}</p>
            )}

            {/* ── Analyst target ── */}
            <div className="col-span-2 border-t pt-3 mt-2 space-y-1">
              {fund.target_price != null ? (
                <>
                  <Row label="Analyst Target" value={fund.target_price.toFixed(2)} />
                  {fund.upside_pct != null && (
                    <div className="flex gap-2 text-sm">
                      <dt className="font-medium text-gray-500 w-32 shrink-0">Expected Upside</dt>
                      <dd className={`font-semibold ${fund.upside_pct >= 0 ? "text-green-600" : "text-red-500"}`}>
                        {fund.upside_pct >= 0 ? "+" : ""}{fund.upside_pct.toFixed(1)}%
                        {fund.is_dr && fund.parent_symbol && (
                          <span
                            title={`Upside calculated using ${fund.parent_symbol} price${fund.upside_reference_price != null ? ` ($${fund.upside_reference_price.toFixed(2)})` : ""}`}
                            className="ml-1.5 text-xs font-semibold px-1 py-0.5 rounded border border-blue-300 text-blue-600 bg-blue-50 cursor-help"
                          >
                            DR → {fund.parent_symbol}
                          </span>
                        )}
                      </dd>
                    </div>
                  )}
                  <Row
                    label="Source"
                    value={
                      fund.analyst_count != null
                        ? `Analyst consensus (${fund.analyst_count} analyst${fund.analyst_count !== 1 ? "s" : ""})`
                        : "Analyst consensus"
                    }
                  />
                </>
              ) : (
                <p className="text-xs text-gray-400">No analyst coverage available.</p>
              )}
            </div>
          </div>
        )}
      </section>

      {/* ── News ── */}
      <section className="bg-white border rounded-xl p-5 shadow-sm">
        <h2 className="text-lg font-semibold mb-3">
          Recent News{news && !("error" in news) ? ` (${news.news_count})` : ""}
        </h2>
        {!news ? (
          <p className="text-sm text-gray-400">No news data.</p>
        ) : "error" in news ? (
          <p className="text-red-400 text-sm">{(news as { error: string }).error}</p>
        ) : news.news.length === 0 ? (
          <p className="text-sm text-gray-500">No recent news.</p>
        ) : (
          <ul className="divide-y">
            {news.news.map((item, i) => (
              <li key={i} className="py-3">
                <a href={item.link} target="_blank" rel="noopener noreferrer"
                  className="text-sm font-medium text-blue-600 hover:underline">
                  {item.title}
                </a>
                <p className="text-xs text-gray-400 mt-0.5">
                  {item.publisher} · {item.published
                    ? new Date(item.published).toLocaleDateString("th-TH", { timeZone: TZ, day: "2-digit", month: "short", year: "2-digit" })
                    : ""}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
