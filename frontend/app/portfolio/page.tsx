"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import PortfolioTable from "@/components/PortfolioTable";
import PortfolioSummary from "@/components/PortfolioSummary";
import { usePortfolio } from "@/lib/PortfolioContext";
import AnalyzeAllButton from "@/components/AnalyzeAllButton";
import { getHoldings, addHolding, removeHolding, analyzeSymbol, updateSwapPermission, getPortfolioPrices } from "@/lib/api";
import type { PortfolioItem, FullAnalysis, AnalyzeAllResult } from "@/lib/api";

const PortfolioPieChart = dynamic(
  () => import("@/components/PortfolioPieChart"),
  { ssr: false, loading: () => <div className="h-[280px] animate-pulse bg-gray-100 rounded-xl" /> }
);

const cashKey = (id: number) => `portfolio_cash_${id}`;
const PRICE_REFRESH_INTERVAL = 60_000; // 60 seconds

function useSecondsAgo(since: Date | null): number {
  const [secs, setSecs] = useState(0);
  useEffect(() => {
    if (!since) { setSecs(0); return; }
    setSecs(Math.floor((Date.now() - since.getTime()) / 1000));
    const id = setInterval(
      () => setSecs(Math.floor((Date.now() - since.getTime()) / 1000)),
      1000
    );
    return () => clearInterval(id);
  }, [since]);
  return secs;
}

export default function PortfolioPage() {
  const { activeId, loading: ctxLoading } = usePortfolio();

  const [items, setItems] = useState<PortfolioItem[]>([]);
  const [cashBalance, setCashBalance] = useState(0);
  const [cashInput, setCashInput] = useState("0");
  const [editingCash, setEditingCash] = useState(false);
  const [symbol, setSymbol] = useState("");
  const [shares, setShares] = useState("");
  const [avgCost, setAvgCost] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Price refresh
  const [refreshingPrices, setRefreshingPrices] = useState(false);
  const [priceRefreshAt, setPriceRefreshAt] = useState<Date | null>(null);
  const secondsAgo = useSecondsAgo(priceRefreshAt);
  const activeIdRef = useRef<number | null>(null);

  const refreshingRef = useRef(false);

  const refreshPrices = useCallback(async (pid: number) => {
    if (refreshingRef.current) return;
    refreshingRef.current = true;
    setRefreshingPrices(true);
    try {
      const prices = await getPortfolioPrices(pid);
      setItems((prev) =>
        prev.map((item) => {
          const p = prices.find((x) => x.symbol === item.symbol);
          return p ? { ...item, current_price: p.current_price, change_percent: p.change_percent, last_updated: p.last_updated } : item;
        })
      );
      setPriceRefreshAt(new Date());
    } catch {
      // silent — prices are best-effort
    } finally {
      refreshingRef.current = false;
      setRefreshingPrices(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    if (activeId == null) return;
    activeIdRef.current = activeId;
    setLoading(true);
    setItems([]);
    setPriceRefreshAt(null);
    const stored = parseFloat(localStorage.getItem(cashKey(activeId)) ?? "0") || 0;
    setCashBalance(stored);
    setCashInput(stored.toString());
    getHoldings(activeId)
      .then((data) => {
        setItems(data);
        setPriceRefreshAt(new Date());
      })
      .finally(() => setLoading(false));
  }, [activeId]);

  // Auto-refresh prices every 60s — uses refs to avoid stale closure
  useEffect(() => {
    if (activeId == null) return;
    const id = setInterval(async () => {
      const pid = activeIdRef.current;
      if (pid == null || refreshingRef.current) return;
      refreshingRef.current = true;
      setRefreshingPrices(true);
      try {
        const prices = await getPortfolioPrices(pid);
        setItems((prev) =>
          prev.map((item) => {
            const p = prices.find((x) => x.symbol === item.symbol);
            return p ? { ...item, current_price: p.current_price, change_percent: p.change_percent, last_updated: p.last_updated } : item;
          })
        );
        setPriceRefreshAt(new Date());
      } catch { /* silent */ } finally {
        refreshingRef.current = false;
        setRefreshingPrices(false);
      }
    }, PRICE_REFRESH_INTERVAL);
    return () => clearInterval(id);
  }, [activeId]);

  function saveCash() {
    if (activeId == null) return;
    const val = parseFloat(cashInput) || 0;
    setCashBalance(val);
    localStorage.setItem(cashKey(activeId), val.toString());
    setEditingCash(false);
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (activeId == null) return;
    setError("");
    try {
      const item = await addHolding(activeId, symbol.trim().toUpperCase(), parseFloat(shares), parseFloat(avgCost));
      setItems((prev) => [...prev, item]);
      setSymbol(""); setShares(""); setAvgCost("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add");
    }
  }

  async function handleRemove(sym: string) {
    if (activeId == null) return;
    await removeHolding(activeId, sym);
    setItems((prev) => prev.filter((i) => i.symbol !== sym));
  }

  async function handleToggleSwap(sym: string, allow_swap: boolean) {
    if (activeId == null) return;
    await updateSwapPermission(activeId, sym, allow_swap);
    setItems((prev) => prev.map((i) => i.symbol === sym ? { ...i, allow_swap } : i));
  }

  function handleAnalyzeAllComplete(result: AnalyzeAllResult) {
    setItems((prev) =>
      prev.map((item) => {
        const r = result.results.find((x) => x.symbol === item.symbol);
        if (!r?.summary || "error" in r.summary) return item;
        const s = r.summary as { signal?: string; confidence?: string; analyzed_at?: string | null };
        return {
          ...item,
          latest_signal: (s.signal ?? item.latest_signal) as PortfolioItem["latest_signal"],
          signal_confidence: (s.confidence ?? item.signal_confidence) as PortfolioItem["signal_confidence"],
          analyzed_at: s.analyzed_at ?? item.analyzed_at,
        };
      })
    );
  }

  async function handleReanalyze(sym: string) {
    const result = await analyzeSymbol(sym);
    const summary = result.summary as { signal?: string; confidence?: string };
    setItems((prev) =>
      prev.map((i) =>
        i.symbol === sym
          ? {
              ...i,
              latest_signal: (summary.signal ?? null) as PortfolioItem["latest_signal"],
              signal_confidence: (summary.confidence ?? null) as PortfolioItem["signal_confidence"],
              analyzed_at: new Date().toISOString(),
            }
          : i
      )
    );
  }

  const hasData = items.length > 0;
  const isLoading = ctxLoading || loading;
  const staleCount = items.filter((i) => {
    if (!i.analyzed_at) return true;
    return (Date.now() - new Date(i.analyzed_at).getTime()) / 60000 > 60;
  }).length;

  const priceLabel = (() => {
    if (refreshingPrices) return "Refreshing…";
    if (!priceRefreshAt) return null;
    if (secondsAgo < 60) return `Updated ${secondsAgo}s ago`;
    return `Updated ${Math.floor(secondsAgo / 60)}m ago`;
  })();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h1 className="text-2xl font-bold">Portfolio</h1>
        <div className="flex items-center gap-3 flex-wrap">
          {hasData && activeId != null && (
            <AnalyzeAllButton
              type="portfolio"
              portfolioId={activeId}
              staleCount={staleCount}
              totalCount={items.length}
              onComplete={handleAnalyzeAllComplete}
            />
          )}
          {hasData && (
            <div className="flex items-center gap-2 text-xs text-gray-400">
              {priceLabel && <span>{priceLabel}</span>}
              <button
                onClick={() => activeId != null && refreshPrices(activeId)}
                disabled={refreshingPrices || activeId == null}
                className="flex items-center gap-1 text-blue-500 hover:text-blue-700 disabled:opacity-40 border border-blue-200 rounded px-2.5 py-1 hover:bg-blue-50 transition-colors"
              >
                <span className={refreshingPrices ? "animate-spin inline-block" : ""}>↻</span>
                Refresh Prices
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── Add stock form ── */}
      <form onSubmit={handleAdd} className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Symbol</label>
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder="AAPL or SCB.BK"
            required
            disabled={activeId == null}
            className="border rounded px-3 py-1.5 text-sm w-32 disabled:opacity-50"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Shares</label>
          <input
            value={shares}
            onChange={(e) => setShares(e.target.value)}
            type="number" min="0" step="any" required
            disabled={activeId == null}
            className="border rounded px-3 py-1.5 text-sm w-24 disabled:opacity-50"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Avg Cost</label>
          <input
            value={avgCost}
            onChange={(e) => setAvgCost(e.target.value)}
            type="number" min="0" step="any" required
            disabled={activeId == null}
            className="border rounded px-3 py-1.5 text-sm w-28 disabled:opacity-50"
          />
        </div>
        <button
          type="submit"
          disabled={activeId == null}
          className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          Add
        </button>
        {error && <p className="text-red-500 text-xs self-center">{error}</p>}
      </form>

      {isLoading ? (
        <p className="text-sm text-gray-400">Loading…</p>
      ) : (
        <>
          {hasData && (
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-start">
              <div className="lg:col-span-2 bg-white border rounded-xl p-4 shadow-sm">
                <h2 className="text-sm font-semibold text-gray-600 mb-2">Portfolio Allocation</h2>
                <PortfolioPieChart items={items} cashBalance={cashBalance} />
              </div>

              <div className="lg:col-span-3 space-y-4">
                <div className="bg-white border rounded-xl p-4 shadow-sm flex items-center gap-4">
                  <div className="flex-1">
                    <p className="text-xs text-gray-400 mb-0.5">Cash Balance</p>
                    {editingCash ? (
                      <div className="flex items-center gap-2">
                        <input
                          type="number" min="0" step="any"
                          value={cashInput}
                          onChange={(e) => setCashInput(e.target.value)}
                          onKeyDown={(e) => e.key === "Enter" && saveCash()}
                          autoFocus
                          className="border rounded px-2 py-1 text-sm w-36"
                        />
                        <button onClick={saveCash} className="text-xs bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700">Save</button>
                        <button onClick={() => { setCashInput(cashBalance.toString()); setEditingCash(false); }} className="text-xs text-gray-400 hover:text-gray-600">Cancel</button>
                      </div>
                    ) : (
                      <p className="text-xl font-bold text-gray-800">
                        {cashBalance.toLocaleString("th-TH", { minimumFractionDigits: 2 })}
                      </p>
                    )}
                  </div>
                  {!editingCash && (
                    <button onClick={() => setEditingCash(true)} className="text-xs text-blue-500 hover:text-blue-700 border border-blue-200 rounded px-3 py-1">Edit</button>
                  )}
                </div>
                <PortfolioSummary items={items} cashBalance={cashBalance} />
              </div>
            </div>
          )}

          <PortfolioTable
            rows={items}
            onRemove={handleRemove}
            onReanalyze={handleReanalyze}
            onToggleSwap={handleToggleSwap}
          />
        </>
      )}
    </div>
  );
}
