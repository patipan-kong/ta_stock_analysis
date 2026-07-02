"use client";

import type { BenchmarkAnalyticsMetrics } from "@/lib/api";
import { fmtNum, pnlColorClass, BENCHMARK_OPTIONS } from "@/lib/analytics-transformers";
import { KPICard, SkeletonCard } from "./KPICard";

interface BenchmarkComparisonGridProps {
  benchmarkMetrics: BenchmarkAnalyticsMetrics | null;
  benchmark: string;
  onBenchmarkChange: (b: string) => void;
  loading?: boolean;
}

export default function BenchmarkComparisonGrid({
  benchmarkMetrics: bm,
  benchmark,
  onBenchmarkChange,
  loading,
}: BenchmarkComparisonGridProps) {
  const primaryBm = bm?.benchmarks?.[0] ?? null;
  const vsLabel = primaryBm ? `vs ${primaryBm.symbol}` : undefined;

  return (
    <div className="space-y-4">
      {/* Benchmark selector — lives with the metrics it controls */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500 font-medium">Benchmark</span>
        <select
          value={benchmark}
          onChange={(e) => onBenchmarkChange(e.target.value)}
          className="text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 text-gray-700 bg-white focus:outline-none focus:ring-1 focus:ring-blue-300 hover:border-gray-300 cursor-pointer"
        >
          {BENCHMARK_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          <KPICard
            label="Alpha"
            value={primaryBm?.alpha != null ? `${primaryBm.alpha >= 0 ? "+" : ""}${primaryBm.alpha.toFixed(2)}%` : "—"}
            valueClass={pnlColorClass(primaryBm?.alpha)}
            sub={vsLabel}
            tooltip="Excess return above the benchmark (annualized, from OLS regression)"
            compact
          />
          <KPICard
            label="Beta"
            value={primaryBm?.beta != null ? fmtNum(primaryBm.beta) : "—"}
            valueClass={
              primaryBm?.beta == null  ? "text-gray-500"
              : primaryBm.beta > 1.2   ? "text-amber-700"
              : primaryBm.beta < 0.5   ? "text-blue-700"
              : "text-gray-800"
            }
            sub={vsLabel}
            tooltip="Sensitivity to benchmark moves. 1.0 = moves in lockstep"
            compact
          />
          <KPICard
            label="R²"
            value={primaryBm?.r_squared != null ? fmtNum(primaryBm.r_squared) : "—"}
            valueClass={"text-gray-800"}
            sub={vsLabel}
            tooltip=""
            compact
          />
          <KPICard
            label="Correlation"
            value={primaryBm?.correlation != null ? fmtNum(primaryBm.correlation) : "—"}
            sub={vsLabel}
            tooltip="Correlation coefficient of daily returns with the benchmark"
            compact
          />
          <KPICard
            label="Tracking Error"
            value={primaryBm?.tracking_error_pct != null ? `${primaryBm.tracking_error_pct.toFixed(2)}%` : "—"}
            sub={vsLabel}
            tooltip="Annualized standard deviation of the return difference vs the benchmark"
            compact
          />
          <KPICard
            label="Info Ratio"
            value={primaryBm?.information_ratio != null ? fmtNum(primaryBm.information_ratio) : "—"}
            valueClass={
              primaryBm?.information_ratio == null  ? "text-gray-500"
              : primaryBm.information_ratio >= 0.5  ? "text-green-700"
              : primaryBm.information_ratio >= 0    ? "text-gray-800"
              : "text-red-600"
            }
            sub={vsLabel}
            tooltip="Active return / tracking error. Measures quality of alpha generation"
            compact
          />
        </div>
      )}
    </div>
  );
}
