"use client";

import { useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { usePortfolio } from "@/lib/PortfolioContext";
import PortfolioTabs from "@/components/PortfolioTabs";
import {
  generateSnapshot,
  getSnapshots,
  getPerformanceComparison,
  benchmarkBackfill,
} from "@/lib/api";
import type {
  PortfolioSnapshotRow,
  GenerateSnapshotResult,
  PerformanceComparisonResult,
} from "@/lib/api";

const EquityCurve = dynamic(() => import("@/components/EquityCurveChart"), {
  ssr: false,
  loading: () => <div className="h-72 animate-pulse bg-gray-100 rounded-xl" />,
});

const BenchmarkChart = dynamic(() => import("@/components/BenchmarkComparisonChart"), {
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
  const [, setLatestResult] = useState<GenerateSnapshotResult | null>(null);
  const [showHoldings, setShowHoldings] = useState(false);

  const [perfData, setPerfData] = useState<PerformanceComparisonResult | null>(null);
  const [perfLoading, setPerfLoading] = useState(false);
  const [backfilling, setBackfilling] = useState(false);

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

  const loadPerfData = useCallback(async () => {
    if (!portfolioId) return;
    setPerfLoading(true);
    try {
      const data = await getPerformanceComparison(portfolioId);
      setPerfData(data);
    } catch {
      // silently ignore — chart section shows empty state
    } finally {
      setPerfLoading(false);
    }
  }, [portfolioId]);

  useEffect(() => {
    loadSnapshots();
    loadPerfData();
  }, [loadSnapshots, loadPerfData]);

  const handleBackfill = async () => {
    setBackfilling(true);
    try {
      const result = await benchmarkBackfill();
      setToast(`Benchmark data seeded — ${result.total_rows_written} rows written.`);
      await loadPerfData();
    } catch (e) {
      setToast(e instanceof Error ? e.message : "Backfill failed");
    } finally {
      setBackfilling(false);
    }
  };

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



  return (
    <main className="max-w-5xl mx-auto px-4 py-6 space-y-6">
      {/* Portfolio hub tabs (Phase 4C.2A) */}
      <PortfolioTabs />

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
        <>
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
              label="Investment Return"
              value={pct(latest.investment_return_pct ?? latest.daily_return_pct)}
              sub={prev ? `pure market gain vs ${prev.snapshot_date}` : "first snapshot"}
              valueClass={pnlColor(latest.investment_return_pct ?? latest.daily_return_pct)}
            />
          </div>

          {/* Non-performance disclosure — shown whenever any external event occurred */}
          {((latest.net_external_cash_flow != null && latest.net_external_cash_flow !== 0) ||
            (latest.imported_asset_value != null && latest.imported_asset_value !== 0) ||
            (latest.manual_adjustment_value != null && latest.manual_adjustment_value !== 0)) && (
            <div className="flex items-start gap-3 px-4 py-3 bg-blue-50 border border-blue-200 rounded-xl text-xs text-blue-800">
              <span className="mt-0.5 text-blue-500 shrink-0">ℹ</span>
              <div className="space-y-1.5">
                <p className="font-semibold">Non-Performance Events Recorded — Excluded from Return</p>
                <div className="flex flex-wrap gap-x-6 gap-y-1 text-blue-700">
                  {(latest.net_external_cash_flow ?? 0) !== 0 && (
                    <span className="flex items-center gap-1.5">
                      <span className="px-1.5 py-0.5 bg-blue-100 rounded text-blue-700 font-medium">External Funding</span>
                      <strong className={(latest.net_external_cash_flow ?? 0) >= 0 ? "text-blue-700" : "text-amber-700"}>
                        {(latest.net_external_cash_flow ?? 0) >= 0 ? "+" : ""}{fmt(latest.net_external_cash_flow)}
                      </strong>
                    </span>
                  )}
                  {(latest.imported_asset_value ?? 0) > 0 && (
                    <span className="flex items-center gap-1.5">
                      <span className="px-1.5 py-0.5 bg-purple-100 rounded text-purple-700 font-medium">Imported Assets</span>
                      <strong className="text-purple-700">+{fmt(latest.imported_asset_value)}</strong>
                    </span>
                  )}
                  {(latest.manual_adjustment_value ?? 0) !== 0 && (
                    <span className="flex items-center gap-1.5">
                      <span className="px-1.5 py-0.5 bg-orange-100 rounded text-orange-700 font-medium">Quantity Correction</span>
                      <strong className="text-orange-700">
                        {(latest.manual_adjustment_value ?? 0) >= 0 ? "+" : ""}{fmt(latest.manual_adjustment_value)}
                      </strong>
                    </span>
                  )}
                  {latest.investment_return_amount != null && (
                    <span className="flex items-center gap-1.5">
                      <span className="px-1.5 py-0.5 bg-green-100 rounded text-green-700 font-medium">Investment Gain</span>
                      <strong className={pnlColor(latest.investment_return_amount)}>
                        {latest.investment_return_amount >= 0 ? "+" : ""}{fmt(latest.investment_return_amount)}
                        {latest.investment_return_pct != null && (
                          <span className="font-normal ml-1">({pct(latest.investment_return_pct)})</span>
                        )}
                      </strong>
                    </span>
                  )}
                </div>
                <p className="text-blue-600">
                  Cash deposits, imported positions, and quantity corrections are balance-sheet events — only pure market movement counts toward your return.
                </p>
              </div>
            </div>
          )}

          {/* Period return decomposition — shown when sells/dividends/fees occurred this period */}
          {((latest.period_realized_pnl != null && latest.period_realized_pnl !== 0) ||
            (latest.period_dividend_income != null && latest.period_dividend_income > 0) ||
            (latest.period_fees_paid != null && latest.period_fees_paid > 0)) && (
            <div className="flex items-start gap-3 px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-xs text-gray-700">
              <span className="mt-0.5 text-gray-400 shrink-0">◎</span>
              <div className="space-y-1.5 w-full">
                <p className="font-semibold text-gray-800">Period Return Breakdown</p>
                <div className="flex flex-wrap gap-x-6 gap-y-1">
                  {(latest.period_realized_pnl ?? 0) !== 0 && (
                    <span className="flex items-center gap-1.5">
                      <span className="px-1.5 py-0.5 bg-teal-100 rounded text-teal-700 font-medium">Realized Sells</span>
                      <strong className={pnlColor(latest.period_realized_pnl)}>
                        {(latest.period_realized_pnl ?? 0) >= 0 ? "+" : ""}{fmt(latest.period_realized_pnl)}
                      </strong>
                    </span>
                  )}
                  {(latest.period_dividend_income ?? 0) > 0 && (
                    <span className="flex items-center gap-1.5">
                      <span className="px-1.5 py-0.5 bg-green-100 rounded text-green-700 font-medium">Dividends</span>
                      <strong className="text-green-700">+{fmt(latest.period_dividend_income)}</strong>
                    </span>
                  )}
                  {(latest.period_fees_paid ?? 0) > 0 && (
                    <span className="flex items-center gap-1.5">
                      <span className="px-1.5 py-0.5 bg-red-100 rounded text-red-600 font-medium">Fees Paid</span>
                      <strong className="text-red-600">−{fmt(latest.period_fees_paid)}</strong>
                    </span>
                  )}
                </div>
                {(latest.period_realized_pnl ?? 0) > 0 &&
                  latest.investment_return_amount != null &&
                  (latest.period_realized_pnl ?? 0) > Math.abs(latest.investment_return_amount) * 1.5 && (
                  <p className="text-gray-500 leading-relaxed">
                    The realized P/L ({fmt(latest.period_realized_pnl)}) is larger than today&apos;s investment return ({fmt(latest.investment_return_amount)}) because most of that gain accumulated over previous periods as unrealized appreciation — today&apos;s return reflects only the price movement since the last snapshot.
                  </p>
                )}
              </div>
            </div>
          )}
        </>
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

      </div>

      {/* Benchmark comparison */}
      <div className="bg-white border rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-sm font-semibold text-gray-700">vs Benchmarks (base = 100)</h2>
            {perfData?.base_date && (
              <p className="text-xs text-gray-400 mt-0.5">
                Normalised from {perfData.base_date} · ^SET.BK (SET) &amp; QQQ
              </p>
            )}
          </div>
          <button
            onClick={handleBackfill}
            disabled={backfilling}
            className="px-3 py-1.5 text-xs font-medium text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {backfilling ? "Seeding…" : "Seed Benchmark Data"}
          </button>
        </div>
        {perfLoading ? (
          <div className="h-72 animate-pulse bg-gray-100 rounded-lg" />
        ) : !perfData || perfData.data.length === 0 ? (
          <div className="h-72 flex flex-col items-center justify-center gap-3 text-gray-400 text-sm">
            <p>No benchmark data yet.</p>
            <button
              onClick={handleBackfill}
              disabled={backfilling}
              className="px-4 py-2 text-xs font-medium text-blue-700 border border-blue-300 rounded-lg hover:bg-blue-50 disabled:opacity-50 transition-colors"
            >
              {backfilling ? "Seeding…" : "Seed Benchmark Data"}
            </button>
          </div>
        ) : (
          <BenchmarkChart comparison={perfData} />
        )}
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
                  <th className="py-2 pr-4 font-medium text-right">Invest. Return</th>
                  <th className="py-2 pr-4 font-medium text-right">Period Activity</th>
                  <th className="py-2 font-medium text-right">Holdings</th>
                </tr>
              </thead>
              <tbody>
                {[...snapshots].reverse().map((s) => {
                  const hasCashFlow = s.net_external_cash_flow != null && s.net_external_cash_flow !== 0;
                  const hasImport = (s.imported_asset_value ?? 0) > 0;
                  const hasAdj = (s.manual_adjustment_value ?? 0) !== 0;
                  const hasAnyExcluded = hasCashFlow || hasImport || hasAdj;
                  const hasSell = (s.period_realized_pnl ?? 0) !== 0;
                  const hasDividend = (s.period_dividend_income ?? 0) > 0;
                  const hasFees = (s.period_fees_paid ?? 0) > 0;
                  return (
                    <tr key={s.id} className={`border-b last:border-0 hover:bg-gray-50 ${hasAnyExcluded ? "bg-blue-50/40" : ""}`}>
                      <td className="py-2 pr-4 font-medium text-gray-800">{s.snapshot_date}</td>
                      <td className="py-2 pr-4 text-right text-gray-700">{fmt(s.total_value)}</td>
                      <td className={`py-2 pr-4 text-right font-medium ${pnlColor(s.unrealized_pnl)}`}>
                        {s.unrealized_pnl != null && s.unrealized_pnl >= 0 ? "+" : ""}{fmt(s.unrealized_pnl)}
                      </td>
                      <td className={`py-2 pr-4 text-right font-medium ${pnlColor(s.realized_pnl)}`}>
                        {s.realized_pnl != null && s.realized_pnl >= 0 ? "+" : ""}{fmt(s.realized_pnl)}
                      </td>
                      <td className={`py-2 pr-4 text-right font-medium ${pnlColor(s.investment_return_pct ?? s.daily_return_pct)}`}>
                        {pct(s.investment_return_pct ?? s.daily_return_pct)}
                        {s.investment_return_amount != null && (
                          <span className="block text-gray-400 font-normal text-xs">
                            {s.investment_return_amount >= 0 ? "+" : ""}{fmt(s.investment_return_amount)}
                          </span>
                        )}
                      </td>
                      <td className="py-2 pr-4 text-right text-xs space-y-0.5">
                        {/* Excluded events (balance-sheet) */}
                        {hasCashFlow && (
                          <div className={`font-medium ${(s.net_external_cash_flow ?? 0) > 0 ? "text-blue-600" : "text-amber-600"}`}>
                            {(s.net_external_cash_flow ?? 0) > 0 ? "+" : ""}{fmt(s.net_external_cash_flow)}
                            <span className="ml-1 text-gray-400 font-normal">cash</span>
                          </div>
                        )}
                        {hasImport && (
                          <div className="font-medium text-purple-600">
                            +{fmt(s.imported_asset_value)}
                            <span className="ml-1 text-gray-400 font-normal">import</span>
                          </div>
                        )}
                        {hasAdj && (
                          <div className="font-medium text-orange-600">
                            {(s.manual_adjustment_value ?? 0) >= 0 ? "+" : ""}{fmt(s.manual_adjustment_value)}
                            <span className="ml-1 text-gray-400 font-normal">adj</span>
                          </div>
                        )}
                        {/* Performance events (included in return) */}
                        {hasSell && (
                          <div className={`font-medium ${(s.period_realized_pnl ?? 0) >= 0 ? "text-teal-600" : "text-red-500"}`}>
                            {(s.period_realized_pnl ?? 0) >= 0 ? "+" : ""}{fmt(s.period_realized_pnl)}
                            <span className="ml-1 text-gray-400 font-normal">realized</span>
                          </div>
                        )}
                        {hasDividend && (
                          <div className="font-medium text-green-600">
                            +{fmt(s.period_dividend_income)}
                            <span className="ml-1 text-gray-400 font-normal">div</span>
                          </div>
                        )}
                        {hasFees && (
                          <div className="font-medium text-red-400">
                            −{fmt(s.period_fees_paid)}
                            <span className="ml-1 text-gray-400 font-normal">fees</span>
                          </div>
                        )}
                        {!hasAnyExcluded && !hasSell && !hasDividend && !hasFees && (
                          <span className="text-gray-300">—</span>
                        )}
                      </td>
                      <td className="py-2 text-right text-gray-500">{s.holdings_count ?? "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </main>
  );
}
