"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import dynamic from "next/dynamic";
import { usePortfolio } from "@/lib/PortfolioContext";
import PortfolioTabs from "@/components/PortfolioTabs";
import {
  getPerformanceStats,
  getPerformanceComparison,
  benchmarkBackfill,
} from "@/lib/api";
import type {
  PerformanceStatsResult,
  PerformanceComparisonResult,
} from "@/lib/api";
import {
  DATE_RANGE_OPTIONS,
  filterByDateRange,
  rebaseToHundred,
  extractDrawdownSeries,
} from "@/lib/analytics-transformers";
import type { DateRangeKey } from "@/lib/analytics-transformers";

import AnalyticsFilters from "@/components/analytics/AnalyticsFilters";
import PortfolioPerformanceGrid from "@/components/analytics/PortfolioPerformanceGrid";
import BenchmarkComparisonGrid from "@/components/analytics/BenchmarkComparisonGrid";
import MonthlyHeatmap from "@/components/analytics/MonthlyHeatmap";

// Recharts components — lazy loaded to avoid SSR
const EquityCurveChart = dynamic(
  () => import("@/components/analytics/EquityCurveChart"),
  { ssr: false, loading: () => <div className="h-72 animate-pulse bg-gray-100 rounded-xl" /> },
);

const DrawdownChart = dynamic(
  () => import("@/components/analytics/DrawdownChart"),
  { ssr: false, loading: () => <div className="h-36 animate-pulse bg-gray-100 rounded-xl" /> },
);

const SignalAnalyticsPanel = dynamic(
  () => import("@/components/analytics/SignalAnalyticsPanel"),
  { ssr: false, loading: () => <div className="h-48 animate-pulse bg-gray-100 rounded-xl" /> },
);

const AllocationAnalyticsPanel = dynamic(
  () => import("@/components/analytics/AllocationAnalyticsPanel"),
  { ssr: false, loading: () => <div className="h-48 animate-pulse bg-gray-100 rounded-xl" /> },
);

// ─── Section wrapper ──────────────────────────────────────────────────────────

function Section({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <h2 className="text-sm font-semibold text-gray-800">{title}</h2>
        {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

// ─── No-data state ────────────────────────────────────────────────────────────

function EmptyState({ message }: { message: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-10 text-center">
      <p className="text-gray-400 text-sm">{message}</p>
      <p className="text-gray-300 text-xs mt-1">
        Go to the Performance page → Generate Snapshot to start building history.
      </p>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const { portfolios, activeId } = usePortfolio();

  const [stats, setStats] = useState<PerformanceStatsResult | null>(null);
  const [comparison, setComparison] = useState<PerformanceComparisonResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [dateRange, setDateRange] = useState<DateRangeKey>("ALL");
  const [benchmark, setBenchmark] = useState("^SET.BK,QQQ");
  const [backfilling, setBackfilling] = useState(false);
  const [backfillMsg, setBackfillMsg] = useState<string | null>(null);

  const portfolioName = portfolios.find((p) => p.id === activeId)?.name ?? "—";

  // ── Fetch ────────────────────────────────────────────────────────────────────
  const load = useCallback(async () => {
    if (!activeId) return;
    setLoading(true);
    setError(null);
    try {
      const [s, c] = await Promise.all([
        getPerformanceStats(activeId, { benchmark, includeEquityCurve: true, includeSectorEvolution: false }),
        getPerformanceComparison(activeId, benchmark),
      ]);
      setStats(s);
      setComparison(c);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }, [activeId, benchmark]);

  const handleBackfill = useCallback(async () => {
    setBackfilling(true);
    setBackfillMsg(null);
    try {
      const r = await benchmarkBackfill("2026-01-01", benchmark);
      setBackfillMsg(`Backfill complete — ${r.total_rows_written} rows written. Reloading…`);
      setTimeout(() => { load(); setBackfillMsg(null); }, 1500);
    } catch {
      setBackfillMsg("Backfill failed — check server logs.");
    } finally {
      setBackfilling(false);
    }
  }, [benchmark, load]);

  useEffect(() => {
    load();
  }, [load]);

  // ── Derived chart data (filtered + rebased) ──────────────────────────────────
  const equityData = useMemo(() => {
    if (!comparison?.data?.length) return [];
    const filtered = filterByDateRange(comparison.data, dateRange);
    const keys = (comparison.series ?? []).map((s) => s.key);
    return rebaseToHundred(filtered, keys);
  }, [comparison, dateRange]);

  const drawdownData = useMemo(() => {
    if (!stats?.equity_curve?.length) return [];
    const filtered = filterByDateRange(stats.equity_curve, dateRange);
    return extractDrawdownSeries(filtered);
  }, [stats, dateRange]);

  // ── No portfolio ─────────────────────────────────────────────────────────────
  if (!activeId) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <p className="text-center text-gray-400 text-sm">
          Select a portfolio from the navbar to view analytics.
        </p>
      </div>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          {error}
          <button
            onClick={load}
            className="ml-4 underline hover:no-underline text-xs"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const pm = stats?.portfolio_metrics ?? null;
  const hasData = pm != null && (pm.snapshot_count ?? 0) > 0;

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-5">
      {/* ── Portfolio hub tabs (Phase 4C.2A) ──────────────────────────────── */}
      <PortfolioTabs />

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-lg font-bold text-gray-900">Analytics</h1>
        <p className="text-xs text-gray-400 mt-0.5">
          Quantitative performance breakdown · KPIs reflect full available snapshot history
        </p>
      </div>

      {/* ── Filters ────────────────────────────────────────────────────────── */}
      <AnalyticsFilters
        portfolioName={portfolioName}
        snapshotCount={pm?.snapshot_count}
        dateFrom={pm?.date_range?.from}
        dateTo={pm?.date_range?.to}
      />

      {/* ── Portfolio performance (absolute — does not depend on benchmark) ──── */}
      <Section
        title="Portfolio Performance"
        subtitle="Describes the portfolio on its own — these figures do not change when you switch benchmarks below"
      >
        <PortfolioPerformanceGrid
          portfolioMetrics={pm}
          allocationMetrics={stats?.allocation_metrics ?? null}
          loading={loading}
        />
      </Section>

      {/* ── Empty state ────────────────────────────────────────────────────── */}
      {!loading && !hasData && (
        <EmptyState message="No snapshot history found for this portfolio." />
      )}

      {/* Monthly returns */}
      {(loading || hasData) && (
        <Section
          title="Monthly Returns"
          subtitle="Calendar heatmap - compounded within year for annual total"
        >
          {loading ? (
            <div className="h-48 animate-pulse bg-gray-100 rounded-xl" />
          ) : (
            <MonthlyHeatmap
              monthlyReturns={pm?.monthly_win_rate?.monthly_returns ?? []}
            />
          )}
        </Section>
      )}

      {/* ── Benchmark comparison (relative — updates when benchmark changes) ── */}
      {(loading || hasData) && (
        <Section
          title="Benchmark Comparison"
          subtitle="How the portfolio performed relative to the selected benchmark"
        >
          <BenchmarkComparisonGrid
            benchmarkMetrics={stats?.benchmark_metrics ?? null}
            benchmark={benchmark}
            onBenchmarkChange={setBenchmark}
            loading={loading}
          />
        </Section>
      )}

      {/* Performance charts */}
      {(loading || hasData) && (
        <Section
          title="Performance Charts"
          subtitle="Drawdown and normalized equity curve for the selected time range"
        >
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <span className="text-xs text-gray-500 font-medium">Time Range</span>
              <div className="flex items-center gap-0.5 bg-gray-100 rounded-lg p-0.5 w-fit">
                {DATE_RANGE_OPTIONS.map((r) => (
                  <button
                    key={r}
                    onClick={() => setDateRange(r)}
                    className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                      dateRange === r
                        ? "bg-white text-blue-700 shadow-sm"
                        : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="mb-3">
                <h3 className="text-xs font-semibold text-gray-700">Drawdown</h3>
                <p className="text-xs text-gray-400 mt-0.5">
                  Peak-to-trough decline from historical high-water mark
                </p>
              </div>
              {loading ? (
                <div className="h-36 animate-pulse bg-gray-100 rounded-xl" />
              ) : (
                <DrawdownChart
                  data={drawdownData}
                  maxDrawdown={pm?.max_drawdown?.max_drawdown_pct}
                />
              )}
            </div>

            <div className="pt-5 border-t border-gray-100">
              <div className="mb-3">
                <h3 className="text-xs font-semibold text-gray-700">Equity Curve</h3>
                <p className="text-xs text-gray-400 mt-0.5">
                  Portfolio vs benchmark - normalized to 100 at the selected start. Benchmarks shown as dashed lines.
                </p>
              </div>
              {loading ? (
                <div className="h-72 animate-pulse bg-gray-100 rounded-xl" />
              ) : (
                <EquityCurveChart
                  data={equityData}
                  series={comparison?.series ?? []}
                />
              )}
            </div>
          </div>
        </Section>
      )}

      {/* ── Signal analytics ─────────────────────────────────────────────────── */}
      {(loading || hasData) && (
        <Section
          title="Signal Analytics"
          subtitle="Holding-period returns, signal decay, and distribution from optimizer signals"
        >
          {loading ? (
            <div className="h-48 animate-pulse bg-gray-100 rounded-xl" />
          ) : (
            <SignalAnalyticsPanel metrics={stats?.signal_metrics ?? null} />
          )}
        </Section>
      )}

      {/* ── Allocation analytics ────────────────────────────────────────────── */}
      {(loading || hasData) && (
        <Section
          title="Allocation Analytics"
          subtitle="Sector contribution, position-level P/L, and cash utilization"
        >
          {loading ? (
            <div className="h-64 animate-pulse bg-gray-100 rounded-xl" />
          ) : (
            <AllocationAnalyticsPanel metrics={stats?.allocation_metrics ?? null} />
          )}
        </Section>
      )}

      

      {/* ── Data freshness footer ───────────────────────────────────────────── */}
      {stats && (
        <p className="text-xs text-gray-300 text-right">
          Generated {new Date(stats.generated_at).toLocaleString()} · 15-min server cache
        </p>
      )}
    </div>
  );
}
