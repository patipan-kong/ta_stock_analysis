"use client";

import type { DateRangeKey } from "@/lib/analytics-transformers";
import { DATE_RANGE_OPTIONS } from "@/lib/analytics-transformers";

const BENCHMARK_OPTIONS = [
  { label: "SET + QQQ",   value: "^SET.BK,QQQ" },
  { label: "SET Index",   value: "^SET.BK" },
  { label: "QQQ (NASDAQ-100)", value: "QQQ" },
  { label: "SPY (S&P 500)", value: "SPY" },
];

interface AnalyticsFiltersProps {
  portfolioName: string;
  dateRange: DateRangeKey;
  onDateRangeChange: (r: DateRangeKey) => void;
  benchmark: string;
  onBenchmarkChange: (b: string) => void;
  snapshotCount?: number;
  dateFrom?: string;
  dateTo?: string;
}

export default function AnalyticsFilters({
  portfolioName,
  dateRange,
  onDateRangeChange,
  benchmark,
  onBenchmarkChange,
  snapshotCount,
  dateFrom,
  dateTo,
}: AnalyticsFiltersProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-3 flex-wrap">
      {/* Portfolio context */}
      <div className="flex items-center gap-2 mr-auto">
        <span className="text-xs text-gray-500 font-medium uppercase tracking-wider">Portfolio</span>
        <span className="text-sm font-semibold text-gray-800">{portfolioName}</span>
        {snapshotCount != null && (
          <span className="text-xs text-gray-400">
            ({snapshotCount} snapshot{snapshotCount !== 1 ? "s" : ""}
            {dateFrom && dateTo ? `, ${dateFrom} – ${dateTo}` : ""})
          </span>
        )}
      </div>

      {/* Benchmark selector */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500 font-medium">vs</span>
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

      {/* Date range toggle */}
      <div className="flex items-center gap-0.5 bg-gray-100 rounded-lg p-0.5">
        {DATE_RANGE_OPTIONS.map((r) => (
          <button
            key={r}
            onClick={() => onDateRangeChange(r)}
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
  );
}
