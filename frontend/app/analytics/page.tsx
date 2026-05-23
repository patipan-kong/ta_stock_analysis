"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import dynamic from "next/dynamic";
import { usePortfolio } from "@/lib/PortfolioContext";
import {
  getPerformanceStats,
  getPerformanceComparison,
} from "@/lib/api";
import type {
  PerformanceStatsResult,
  PerformanceComparisonResult,
} from "@/lib/api";
import {
  filterByDateRange,
  rebaseToHundred,
  extractDrawdownSeries,
} from "@/lib/analytics-transformers";
import type { DateRangeKey } from "@/lib/analytics-transformers";

import AnalyticsFilters from "@/components/analytics/AnalyticsFilters";
import KPIGrid from "@/components/analytics/KPIGrid";
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
        dateRange={dateRange}
        onDateRangeChange={setDateRange}
        benchmark={benchmark}
        onBenchmarkChange={(b) => setBenchmark(b)}
        snapshotCount={pm?.snapshot_count}
        dateFrom={pm?.date_range?.from}
        dateTo={pm?.date_range?.to}
      />

      {/* ── KPI grid ───────────────────────────────────────────────────────── */}
      <KPIGrid
        portfolioMetrics={pm}
        benchmarkMetrics={stats?.benchmark_metrics ?? null}
        allocationMetrics={stats?.allocation_metrics ?? null}
        loading={loading}
      />

      {/* ── Empty state ────────────────────────────────────────────────────── */}
      {!loading && !hasData && (
        <EmptyState message="No snapshot history found for this portfolio." />
      )}

      {/* ── Equity curve ──────────────────────────────────────────────────── */}
      {(loading || hasData) && (
        <Section
          title="Equity Curve"
          subtitle="Portfolio vs benchmark — normalized to 100 at the selected start. Benchmarks shown as dashed lines."
        >
          {loading ? (
            <div className="h-72 animate-pulse bg-gray-100 rounded-xl" />
          ) : (
            <EquityCurveChart
              data={equityData}
              series={comparison?.series ?? []}
            />
          )}
        </Section>
      )}

      {/* ── Drawdown ──────────────────────────────────────────────────────── */}
      {(loading || hasData) && (
        <Section
          title="Drawdown"
          subtitle="Peak-to-trough decline from historical high-water mark"
        >
          {loading ? (
            <div className="h-36 animate-pulse bg-gray-100 rounded-xl" />
          ) : (
            <DrawdownChart
              data={drawdownData}
              maxDrawdown={pm?.max_drawdown?.max_drawdown_pct}
            />
          )}
        </Section>
      )}

      {/* ── Monthly returns + Signal analytics ─────────────────────────────── */}
      {(loading || hasData) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <Section
            title="Monthly Returns"
            subtitle="Calendar heatmap — compounded within year for annual total"
          >
            {loading ? (
              <div className="h-48 animate-pulse bg-gray-100 rounded-xl" />
            ) : (
              <MonthlyHeatmap
                monthlyReturns={pm?.monthly_win_rate?.monthly_returns ?? []}
              />
            )}
          </Section>

          <Section
            title="Signal Analytics"
            subtitle="BUY win rate, SELL accuracy, and holding-period returns from optimizer signals"
          >
            {loading ? (
              <div className="h-48 animate-pulse bg-gray-100 rounded-xl" />
            ) : (
              <SignalAnalyticsPanel metrics={stats?.signal_metrics ?? null} />
            )}
          </Section>
        </div>
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

      {/* ── Benchmark detail ────────────────────────────────────────────────── */}
      {!loading && (stats?.benchmark_metrics?.benchmarks?.length ?? 0) > 0 && stats && (
        <Section
          title="Benchmark Comparison Detail"
          subtitle="Alpha/Beta/R² from OLS regression of daily returns against each benchmark"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b">
                  {["Benchmark", "Alpha", "Beta", "R²", "Correlation", "Tracking Err", "Info Ratio", "Days"].map((h) => (
                    <th key={h} className="py-2 pr-4 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {stats.benchmark_metrics.benchmarks.map((b) => {
                  const fmtR = (v: number | null, d = 2) =>
                    v != null ? v.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d }) : "—";
                  const isUnreliable = b.statistical_confidence === "UNRELIABLE";
                  const isLow = b.statistical_confidence === "LOW";
                  const dimClass = isUnreliable ? "opacity-40" : isLow ? "opacity-60" : "";
                  const hasLowSample = b.warnings?.includes("LOW_SAMPLE_SIZE");
                  const hasUnreliableRegression = b.warnings?.includes("UNRELIABLE_REGRESSION");
                  const hasSuspectAlpha = b.warnings?.includes("SUSPECT_ALPHA");
                  return (
                    <tr key={b.symbol} className="border-b last:border-0 hover:bg-gray-50">
                      <td className="py-2.5 pr-4">
                        <span className="font-semibold text-blue-700">{b.symbol}</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {hasLowSample && (
                            <span className="text-xs px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded font-medium">
                              Low sample ({b.aligned_days}d)
                            </span>
                          )}
                          {hasUnreliableRegression && (
                            <span className="text-xs px-1.5 py-0.5 bg-red-100 text-red-600 rounded font-medium">
                              Unreliable regression
                            </span>
                          )}
                          {hasSuspectAlpha && !hasUnreliableRegression && (
                            <span className="text-xs px-1.5 py-0.5 bg-orange-100 text-orange-600 rounded font-medium">
                              Suspect alpha
                            </span>
                          )}
                          {!hasLowSample && !hasUnreliableRegression && !hasSuspectAlpha && (
                            <span className="text-xs text-gray-400">{b.aligned_days}d · {b.data_quality ?? "—"}</span>
                          )}
                        </div>
                      </td>
                      <td className={`py-2.5 pr-4 font-medium tabular-nums ${dimClass} ${b.alpha != null && b.alpha >= 0 ? "text-green-700" : "text-red-600"}`}>
                        {b.alpha != null ? `${b.alpha >= 0 ? "+" : ""}${b.alpha.toFixed(2)}%` : "—"}
                      </td>
                      <td className={`py-2.5 pr-4 text-gray-700 tabular-nums ${dimClass}`}>{fmtR(b.beta)}</td>
                      <td className={`py-2.5 pr-4 text-gray-700 tabular-nums ${dimClass}`}>{fmtR(b.r_squared)}</td>
                      <td className={`py-2.5 pr-4 text-gray-700 tabular-nums ${dimClass}`}>{fmtR(b.correlation)}</td>
                      <td className={`py-2.5 pr-4 text-gray-700 tabular-nums ${dimClass}`}>
                        {b.tracking_error_pct != null ? `${b.tracking_error_pct.toFixed(2)}%` : "—"}
                      </td>
                      <td className={`py-2.5 pr-4 text-gray-700 tabular-nums ${dimClass}`}>{fmtR(b.information_ratio)}</td>
                      <td className="py-2.5 text-gray-500">{b.aligned_days}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {stats.benchmark_metrics.benchmarks.some((b) => (b.warnings?.length ?? 0) > 0) && (
            <p className="mt-3 text-xs text-gray-400">
              Dimmed metrics have limited statistical reliability. Regression requires ≥ 60 aligned trading days for stable estimates;
              results from shorter periods should be treated as indicative only.
            </p>
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
