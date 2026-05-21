"use client";

import { useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { usePortfolio } from "@/lib/PortfolioContext";
import { generateSnapshot, getSnapshots, listPortfolios } from "@/lib/api";
import type { PortfolioSnapshotRow, GenerateSnapshotResult } from "@/lib/api";

const EquityCurve = dynamic(() => import("@/components/EquityCurveChart"), {
  ssr: false,
  loading: () => <div className="h-72 animate-pulse bg-gray-100 rounded-xl" />,
});

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(n: number | null | undefined, decimals = 2): string {
  if (n == null) return "—";
  return n.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function pct(n: number | null | undefined): string {
  if (n == null) return "—";
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

function pnlColor(n: number | null | undefined): string {
  if (n == null) return "text-gray-500";
  return n >= 0 ? "text-green-700" : "text-red-600";
}

// ─── Stat card ────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  valueClass = "text-gray-900",
}: {
  label: string;
  value: string;
  sub?: string;
  valueClass?: string;
}) {
  return (
    <div className="bg-white border rounded-xl p-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-lg font-semibold ${valueClass}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

// ─── Holdings table ───────────────────────────────────────────────────────────

function HoldingsTable({ snapshot }: { snapshot: PortfolioSnapshotRow }) {
  const holdings = snapshot.holdings ?? [];
  if (!holdings.length) return <p className="text-sm text-gray-400">No holdings recorded in this snapshot.</p>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-500 border-b">
            <th className="py-2 pr-4 font-medium">Symbol</th>
            <th className="py-2 pr-4 font-medium text-right">Shares</th>
            <th className="py-2 pr-4 font-medium text-right">Avg Cost</th>
            <th className="py-2 pr-4 font-medium text-right">Price</th>
            <th className="py-2 pr-4 font-medium text-right">Market Value</th>
            <th className="py-2 pr-4 font-medium text-right">Unrealized P/L</th>
            <th className="py-2 font-medium">Sector</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h) => (
            <tr key={h.symbol} className="border-b last:border-0 hover:bg-gray-50">
              <td className="py-2 pr-4 font-medium text-blue-700">{h.symbol}</td>
              <td className="py-2 pr-4 text-right text-gray-700">{fmt(h.shares, 4)}</td>
              <td className="py-2 pr-4 text-right text-gray-700">{fmt(h.avg_cost, 2)}</td>
              <td className="py-2 pr-4 text-right text-gray-700">{fmt(h.current_price, 2)}</td>
              <td className="py-2 pr-4 text-right text-gray-700">{fmt(h.market_value, 2)}</td>
              <td className={`py-2 pr-4 text-right font-medium ${pnlColor(h.unrealized_pnl)}`}>
                {h.unrealized_pnl >= 0 ? "+" : ""}{fmt(h.unrealized_pnl, 2)}
                <span className="text-xs ml-1 font-normal">({pct(h.unrealized_pnl_pct)})</span>
              </td>
              <td className="py-2 text-gray-500 text-xs">{h.sector}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function PerformancePage() {
  const { activeId: activePortfolioId } = usePortfolio();
  const [snapshots, setSnapshots] = useState<PortfolioSnapshotRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [latestResult, setLatestResult] = useState<GenerateSnapshotResult | null>(null);
  const [showHoldings, setShowHoldings] = useState(false);

  const portfolioId = activePortfolioId ?? 0;

  const loadSnapshots = useCallback(async () => {
    if (!portfolioId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getSnapshots(portfolioId);
      setSnapshots(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load snapshots");
    } finally {
      setLoading(false);
    }
  }, [portfolioId]);

  useEffect(() => {
    loadSnapshots();
  }, [loadSnapshots]);

  const handleGenerate = async () => {
    if (!portfolioId) return;
    setGenerating(true);
    setError(null);
    try {
      const result = await generateSnapshot(portfolioId);
      setLatestResult(result);
      setToast(result.updated ? "Snapshot updated for today." : "Snapshot generated for today.");
      await loadSnapshots();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate snapshot");
    } finally {
      setGenerating(false);
    }
  };

  // Auto-clear toast after 3.5s
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(t);
  }, [toast]);

  const latest = snapshots.length > 0 ? snapshots[snapshots.length - 1] : null;
  const prev = snapshots.length > 1 ? snapshots[snapshots.length - 2] : null;

  // Compute total P/L = unrealized + realized for display
  const totalPnl =
    latest
      ? (latest.unrealized_pnl ?? 0) + (latest.realized_pnl ?? 0)
      : null;

  return (
    <main className="max-w-5xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Portfolio Performance</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {snapshots.length > 0
              ? `${snapshots.length} snapshot${snapshots.length !== 1 ? "s" : ""} · earliest ${snapshots[0].snapshot_date}`
              : "No snapshots yet — generate one to start tracking"}
          </p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating || !portfolioId}
          className="px-4 py-2 bg-blue-700 text-white text-sm font-medium rounded-lg hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {generating ? "Generating…" : "Generate Snapshot"}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">
          {error}
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-3 bg-green-700 text-white text-sm font-medium rounded-xl shadow-lg">
          {toast}
        </div>
      )}

      {/* Summary stat cards */}
      {latest && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard
            label="Portfolio Value"
            value={fmt(latest.total_value)}
            sub={`Cash: ${fmt(latest.cash_balance)}`}
          />
          <StatCard
            label="Unrealized P/L"
            value={`${latest.unrealized_pnl != null && latest.unrealized_pnl >= 0 ? "+" : ""}${fmt(latest.unrealized_pnl)}`}
            sub={pct(latest.unrealized_pnl_pct)}
            valueClass={pnlColor(latest.unrealized_pnl)}
          />
          <StatCard
            label="Realized P/L"
            value={`${latest.realized_pnl != null && latest.realized_pnl >= 0 ? "+" : ""}${fmt(latest.realized_pnl)}`}
            valueClass={pnlColor(latest.realized_pnl)}
          />
          <StatCard
            label="Daily Return"
            value={pct(latest.daily_return_pct)}
            sub={prev ? `vs ${prev.snapshot_date}` : "first snapshot"}
            valueClass={pnlColor(latest.daily_return_pct)}
          />
        </div>
      )}

      {/* Equity curve */}
      <div className="bg-white border rounded-xl p-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Equity Curve</h2>
        {loading ? (
          <div className="h-72 animate-pulse bg-gray-100 rounded-lg" />
        ) : snapshots.length === 0 ? (
          <div className="h-72 flex items-center justify-center text-gray-400 text-sm">
            No snapshot data yet. Click &ldquo;Generate Snapshot&rdquo; to begin.
          </div>
        ) : (
          <EquityCurve snapshots={snapshots} />
        )}

        {/* Benchmark placeholder */}
        <p className="text-xs text-gray-400 mt-2 text-right">
          Benchmark comparison coming soon
        </p>
      </div>

      {/* Latest snapshot — holdings detail */}
      {latest && (
        <div className="bg-white border rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-700">
              Latest Snapshot — {latest.snapshot_date}
            </h2>
            <button
              onClick={() => setShowHoldings((v) => !v)}
              className="text-xs text-blue-600 hover:underline"
            >
              {showHoldings ? "Hide holdings" : "Show holdings"}
            </button>
          </div>

          {/* Sector breakdown */}
          {latest.sector_breakdown && Object.keys(latest.sector_breakdown).length > 0 && (
            <div className="mb-4">
              <p className="text-xs text-gray-500 mb-2">Sector allocation (% of total value)</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(latest.sector_breakdown)
                  .sort((a, b) => b[1] - a[1])
                  .map(([sector, pctVal]) => (
                    <span
                      key={sector}
                      className="px-2 py-1 bg-gray-100 rounded-full text-xs text-gray-700"
                    >
                      {sector} <span className="font-medium">{pctVal.toFixed(1)}%</span>
                    </span>
                  ))}
              </div>
            </div>
          )}

          {showHoldings && <HoldingsTable snapshot={latest} />}
        </div>
      )}

      {/* Snapshot history table */}
      {snapshots.length > 0 && (
        <div className="bg-white border rounded-xl p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Snapshot History</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b">
                  <th className="py-2 pr-4 font-medium">Date</th>
                  <th className="py-2 pr-4 font-medium text-right">Total Value</th>
                  <th className="py-2 pr-4 font-medium text-right">Unrealized P/L</th>
                  <th className="py-2 pr-4 font-medium text-right">Realized P/L</th>
                  <th className="py-2 pr-4 font-medium text-right">Daily Return</th>
                  <th className="py-2 font-medium text-right">Holdings</th>
                </tr>
              </thead>
              <tbody>
                {[...snapshots].reverse().map((s) => (
                  <tr key={s.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="py-2 pr-4 font-medium text-gray-800">{s.snapshot_date}</td>
                    <td className="py-2 pr-4 text-right text-gray-700">{fmt(s.total_value)}</td>
                    <td className={`py-2 pr-4 text-right font-medium ${pnlColor(s.unrealized_pnl)}`}>
                      {s.unrealized_pnl != null && s.unrealized_pnl >= 0 ? "+" : ""}{fmt(s.unrealized_pnl)}
                    </td>
                    <td className={`py-2 pr-4 text-right font-medium ${pnlColor(s.realized_pnl)}`}>
                      {s.realized_pnl != null && s.realized_pnl >= 0 ? "+" : ""}{fmt(s.realized_pnl)}
                    </td>
                    <td className={`py-2 pr-4 text-right font-medium ${pnlColor(s.daily_return_pct)}`}>
                      {pct(s.daily_return_pct)}
                    </td>
                    <td className="py-2 text-right text-gray-500">{s.holdings_count ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </main>
  );
}
