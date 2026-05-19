"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import StockCard from "@/components/StockCard";
import SignalBadge from "@/components/SignalBadge";
import { usePortfolio } from "@/lib/PortfolioContext";
import { getHoldings, getWatchlist, analyzeHoldings, analyzeWatchlist, analyzeSymbol } from "@/lib/api";
import type { Portfolio, PortfolioItem, WatchlistItem, FullAnalysis } from "@/lib/api";

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

function latestDate(items: { analyzed_at: string | null }[]): string | null {
  const dates = items.map((i) => i.analyzed_at).filter((d): d is string => d != null);
  return dates.length > 0 ? dates.sort().at(-1)! : null;
}

function Spinner() {
  return (
    <span className="inline-block w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { portfolios, loading: ctxLoading } = usePortfolio();

  const [holdingsMap, setHoldingsMap] = useState<Record<number, PortfolioItem[]>>({});
  const [analysisMap, setAnalysisMap] = useState<Record<number, FullAnalysis[]>>({});
  const [analyzingId, setAnalyzingId] = useState<number | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [analyzingWatchlist, setAnalyzingWatchlist] = useState(false);
  const [analyzingSymbols, setAnalyzingSymbols] = useState<Set<string>>(new Set());
  const [loadingData, setLoadingData] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (ctxLoading || portfolios.length === 0) return;
    setLoadingData(true);
    setAnalysisMap({});

    Promise.all([
      ...portfolios.map((p) =>
        getHoldings(p.id).then((items) => ({ portfolioId: p.id, items }))
      ),
      getWatchlist().then((w) => ({ portfolioId: -1, items: w as unknown as PortfolioItem[] })),
    ])
      .then((results) => {
        const map: Record<number, PortfolioItem[]> = {};
        results.forEach(({ portfolioId, items }) => {
          if (portfolioId === -1) setWatchlist(items as unknown as WatchlistItem[]);
          else map[portfolioId] = items;
        });
        setHoldingsMap(map);
      })
      .catch(() => setError("Cannot connect to backend"))
      .finally(() => setLoadingData(false));
  }, [portfolios, ctxLoading]);

  async function handleAnalyzePortfolio(portfolioId: number) {
    setAnalyzingId(portfolioId);
    setError("");
    try {
      const results = await analyzeHoldings(portfolioId);
      setAnalysisMap((prev) => ({ ...prev, [portfolioId]: results }));
      // Also refresh holdings cached data
      const fresh = await getHoldings(portfolioId);
      setHoldingsMap((prev) => ({ ...prev, [portfolioId]: fresh }));
    } catch {
      setError("Analysis failed");
    } finally {
      setAnalyzingId(null);
    }
  }

  function _applyAnalysisToWatchlist(result: FullAnalysis): Partial<WatchlistItem> {
    const s = result.summary;
    const tech = result.technical as Record<string, unknown>;
    const fund = result.fundamental as Record<string, unknown>;
    return {
      latest_signal:    (s?.signal ?? null) as WatchlistItem["latest_signal"],
      signal_confidence:(s?.confidence ?? null) as WatchlistItem["signal_confidence"],
      analyzed_at:      s?.analyzed_at ?? null,
      reasoning:        s?.reasoning ?? null,
      risks:            s?.risks ?? null,
      ta_score:         typeof tech?.ta_score === "number" ? tech.ta_score : null,
      fa_score:         typeof fund?.fa_score === "number" ? fund.fa_score : null,
    };
  }

  async function handleAnalyzeWatchlist() {
    setAnalyzingWatchlist(true);
    setError("");
    try {
      const results = await analyzeWatchlist();
      setWatchlist((prev) =>
        prev.map((item) => {
          const match = results.find((r) => r.symbol === item.symbol);
          return match ? { ...item, ..._applyAnalysisToWatchlist(match) } : item;
        })
      );
    } catch {
      setError("Watchlist analysis failed");
    } finally {
      setAnalyzingWatchlist(false);
    }
  }

  async function handleAnalyzeSymbol(symbol: string) {
    setAnalyzingSymbols((prev) => new Set([...prev, symbol]));
    setError("");
    try {
      const result = await analyzeSymbol(symbol);
      setWatchlist((prev) =>
        prev.map((item) =>
          item.symbol === symbol
            ? { ...item, ..._applyAnalysisToWatchlist(result) }
            : item
        )
      );
    } catch {
      setError(`Analysis failed for ${symbol}`);
    } finally {
      setAnalyzingSymbols((prev) => {
        const next = new Set(prev);
        next.delete(symbol);
        return next;
      });
    }
  }

  const isLoading = ctxLoading || loadingData;

  return (
    <div className="space-y-10">
      <section>
        <h1 className="text-2xl font-bold mb-1">Dashboard</h1>
        <p className="text-sm text-gray-500">BUY / HOLD / SELL signals for all portfolios</p>
        {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
      </section>

      {isLoading ? (
        <p className="text-sm text-gray-400">Loading…</p>
      ) : (
        <>
          {portfolios.map((portfolio) => (
            <PortfolioSection
              key={portfolio.id}
              portfolio={portfolio}
              holdings={holdingsMap[portfolio.id] ?? []}
              analysis={analysisMap[portfolio.id] ?? []}
              analyzing={analyzingId === portfolio.id}
              onAnalyze={() => handleAnalyzePortfolio(portfolio.id)}
            />
          ))}

          {/* ── Watchlist ── */}
          <section>
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <h2 className="text-xl font-semibold">Watchlist</h2>
              {watchlist.length > 0 && (() => {
                const last = latestDate(watchlist);
                return last ? (
                  <span className="text-xs text-gray-400">Last analyzed: {formatDate(last)}</span>
                ) : null;
              })()}
              {watchlist.length > 0 && (
                <button
                  onClick={handleAnalyzeWatchlist}
                  disabled={analyzingWatchlist}
                  className="ml-auto text-sm bg-blue-600 text-white px-3 py-1.5 rounded hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {analyzingWatchlist && <Spinner />}
                  {analyzingWatchlist ? "Analyzing…" : "Analyze All"}
                </button>
              )}
            </div>

            {watchlist.length === 0 ? (
              <p className="text-gray-500 text-sm">
                Watchlist is empty.{" "}
                <Link href="/watchlist" className="text-blue-500 underline">Add stocks</Link>.
              </p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {watchlist.map((item) => (
                  <WatchlistCard
                    key={item.symbol}
                    item={item}
                    analyzing={analyzingSymbols.has(item.symbol)}
                    onAnalyze={() => handleAnalyzeSymbol(item.symbol)}
                  />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}

// ─── Portfolio Section ────────────────────────────────────────────────────────

function PortfolioSection({
  portfolio, holdings, analysis, analyzing, onAnalyze,
}: {
  portfolio: Portfolio;
  holdings: PortfolioItem[];
  analysis: FullAnalysis[];
  analyzing: boolean;
  onAnalyze: () => void;
}) {
  const lastAnalyzed = latestDate(holdings);

  return (
    <section>
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <h2 className="text-xl font-semibold">{portfolio.name}</h2>
        {lastAnalyzed && (
          <span className="text-xs text-gray-400">Last analyzed: {formatDate(lastAnalyzed)}</span>
        )}
        {holdings.length > 0 && (
          <button
            onClick={onAnalyze}
            disabled={analyzing}
            className="ml-auto text-sm bg-blue-600 text-white px-3 py-1.5 rounded hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            {analyzing && <Spinner />}
            {analyzing ? "Analyzing…" : "Analyze All"}
          </button>
        )}
      </div>

      {holdings.length === 0 ? (
        <p className="text-gray-500 text-sm">
          No stocks in this portfolio.{" "}
          <Link href="/portfolio" className="text-blue-500 underline">Add stocks</Link>.
        </p>
      ) : analysis.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {analysis.map((a) => <StockCard key={a.symbol} analysis={a} />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {holdings.map((item) => <HoldingCard key={item.symbol} item={item} />)}
        </div>
      )}
    </section>
  );
}

// ─── Holding Card (portfolio) ─────────────────────────────────────────────────

function HoldingCard({ item }: { item: PortfolioItem }) {
  const display = item.symbol.replace(".BK", "");
  const cp = item.change_percent;
  const changeClass = cp == null ? "text-gray-400" : cp > 0 ? "text-green-600 font-medium" : "text-red-600 font-medium";
  const changeText = cp == null ? "—" : `${cp > 0 ? "+" : ""}${cp.toFixed(2)}%`;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <Link href={`/stock/${encodeURIComponent(item.symbol)}`}
          className="text-lg font-bold text-blue-600 hover:underline">
          {display}
          {item.symbol.endsWith(".BK") && <span className="ml-1 text-xs text-gray-400">.BK</span>}
        </Link>
        {item.latest_signal
          ? <SignalBadge signal={item.latest_signal} />
          : <span className="text-xs text-gray-300">—</span>}
      </div>

      <div className="flex items-center gap-3 text-sm mb-2">
        <span className="font-semibold text-gray-800">
          {item.current_price != null ? item.current_price.toFixed(2) : "—"}
        </span>
        <span className={changeClass}>{changeText}</span>
        <span className="text-xs text-gray-400 ml-auto">{item.shares} shares</span>
      </div>

      {(item.ta_score != null || item.fa_score != null) && (
        <div className="grid grid-cols-2 gap-2 text-sm text-gray-600 mb-2">
          {item.ta_score != null && <div><span className="font-medium">TA Score:</span> {item.ta_score}</div>}
          {item.fa_score != null && <div><span className="font-medium">FA Score:</span> {item.fa_score}</div>}
        </div>
      )}

      {item.reasoning && (
        <p className="text-xs text-gray-500 line-clamp-2 mb-2">{item.reasoning}</p>
      )}

      {item.analyzed_at && (
        <div className="mt-auto pt-2 border-t border-gray-100 text-xs text-gray-400">
          Analyzed: {formatDate(item.analyzed_at)}
        </div>
      )}
    </div>
  );
}

// ─── Watchlist Card ───────────────────────────────────────────────────────────

function WatchlistCard({
  item, analyzing, onAnalyze,
}: {
  item: WatchlistItem;
  analyzing: boolean;
  onAnalyze: () => void;
}) {
  const display = item.symbol.replace(".BK", "");
  const hasAnalysis = item.latest_signal != null;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <Link href={`/stock/${encodeURIComponent(item.symbol)}`}
          className="text-lg font-bold text-blue-600 hover:underline">
          {display}
          {item.symbol.endsWith(".BK") && <span className="ml-1 text-xs text-gray-400">.BK</span>}
        </Link>
        {hasAnalysis && <SignalBadge signal={item.latest_signal!} />}
      </div>

      {hasAnalysis ? (
        <>
          {(item.ta_score != null || item.fa_score != null) && (
            <div className="grid grid-cols-2 gap-2 text-sm text-gray-600 mb-2">
              {item.ta_score != null && <div><span className="font-medium">TA Score:</span> {item.ta_score}</div>}
              {item.fa_score != null && <div><span className="font-medium">FA Score:</span> {item.fa_score}</div>}
            </div>
          )}
          {item.reasoning && (
            <p className="text-xs text-gray-500 line-clamp-2 mb-2">{item.reasoning}</p>
          )}
          <div className="mt-auto pt-2 border-t border-gray-100 flex items-center justify-between">
            <span className="text-xs text-gray-400">{formatDate(item.analyzed_at)}</span>
            <button
              onClick={onAnalyze}
              disabled={analyzing}
              className="text-xs text-blue-500 hover:underline disabled:opacity-50 flex items-center gap-1"
            >
              {analyzing && <Spinner />}
              {analyzing ? "Analyzing…" : "Re-analyze"}
            </button>
          </div>
        </>
      ) : (
        <button
          onClick={onAnalyze}
          disabled={analyzing}
          className="mt-2 w-full py-2 text-sm border border-blue-200 text-blue-600 rounded-lg hover:bg-blue-50 disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {analyzing ? <><Spinner />Analyzing…</> : "Analyze"}
        </button>
      )}
    </div>
  );
}
