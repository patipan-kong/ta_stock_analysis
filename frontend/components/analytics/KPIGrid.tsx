"use client";

import type {
  PortfolioAnalyticsMetrics,
  BenchmarkAnalyticsMetrics,
  AllocationAnalyticsMetrics,
} from "@/lib/api";
import { fmtPct, fmtNum, pnlColorClass } from "@/lib/analytics-transformers";

interface KPICardProps {
  label: string;
  value: string;
  valueClass?: string;
  sub?: string;
  tooltip?: string;
  highlight?: "positive" | "negative" | "neutral";
}

function KPICard({ label, value, valueClass, sub, tooltip }: KPICardProps) {
  return (
    <div
      className="bg-white border border-gray-200 rounded-xl p-4 hover:border-gray-300 transition-colors"
      title={tooltip}
    >
      <p className="text-xs text-gray-500 mb-1 font-medium">{label}</p>
      <p className={`text-lg font-bold tabular-nums ${valueClass ?? "text-gray-900"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 animate-pulse">
      <div className="h-3 bg-gray-100 rounded w-20 mb-2" />
      <div className="h-6 bg-gray-200 rounded w-24" />
    </div>
  );
}

interface KPIGridProps {
  portfolioMetrics: PortfolioAnalyticsMetrics | null;
  benchmarkMetrics: BenchmarkAnalyticsMetrics | null;
  allocationMetrics: AllocationAnalyticsMetrics | null;
  loading?: boolean;
}

export default function KPIGrid({
  portfolioMetrics: pm,
  benchmarkMetrics: bm,
  allocationMetrics: am,
  loading,
}: KPIGridProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
        {Array.from({ length: 10 }).map((_, i) => <SkeletonCard key={i} />)}
      </div>
    );
  }

  const primaryBm = bm?.benchmarks?.[0] ?? null;

  const totalReturn = pm?.cumulative_return_pct ?? null;
  const annReturn   = pm?.annualized_return_pct ?? null;
  const maxDd       = pm?.max_drawdown?.max_drawdown_pct ?? null;
  const vol         = pm?.volatility_pct ?? null;
  const sharpe      = pm?.sharpe_ratio ?? null;
  const winMonth    = pm?.monthly_win_rate?.win_rate ?? null;
  const alpha       = primaryBm?.alpha ?? null;
  const beta        = primaryBm?.beta ?? null;
  const infoRatio   = primaryBm?.information_ratio ?? null;
  const cashPct     = am?.cash_utilization?.avg_cash_pct ?? null;

  const ddDays = pm?.max_drawdown?.duration_days;
  const ddSub  = ddDays != null ? `${ddDays}d recovery` : undefined;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
      <KPICard
        label="Total Return"
        value={fmtPct(totalReturn)}
        valueClass={pnlColorClass(totalReturn)}
        tooltip="Cumulative portfolio return over the full snapshot history"
      />
      <KPICard
        label="Ann. Return"
        value={fmtPct(annReturn)}
        valueClass={pnlColorClass(annReturn)}
        tooltip="Annualized return (CAGR) scaled to a 365-day year"
      />
      <KPICard
        label="Max Drawdown"
        value={maxDd != null ? `${maxDd.toFixed(2)}%` : "—"}
        valueClass={maxDd != null && maxDd < 0 ? "text-red-600" : "text-gray-900"}
        sub={ddSub}
        tooltip="Largest peak-to-trough decline in portfolio value"
      />
      <KPICard
        label="Volatility"
        value={fmtPct(vol, false)}
        valueClass="text-gray-800"
        tooltip="Annualized standard deviation of daily returns"
      />
      <KPICard
        label="Sharpe Ratio"
        value={sharpe != null ? fmtNum(sharpe) : "—"}
        valueClass={
          sharpe == null ? "text-gray-500"
          : sharpe >= 1   ? "text-green-700"
          : sharpe >= 0   ? "text-gray-800"
          : "text-red-600"
        }
        tooltip="Risk-adjusted return: (return − risk-free rate) / volatility. >1 is good"
      />
      <KPICard
        label="Win Month %"
        value={winMonth != null ? `${winMonth.toFixed(1)}%` : "—"}
        valueClass={
          winMonth == null   ? "text-gray-500"
          : winMonth >= 60   ? "text-green-700"
          : winMonth >= 50   ? "text-gray-800"
          : "text-red-600"
        }
        sub={pm?.monthly_win_rate ? `${pm.monthly_win_rate.wins}W / ${pm.monthly_win_rate.losses}L` : undefined}
        tooltip="Percentage of calendar months with positive returns"
      />
      <KPICard
        label="Alpha"
        value={alpha != null ? fmtPct(alpha * 100) : "—"}
        valueClass={pnlColorClass(alpha)}
        sub={primaryBm ? `vs ${primaryBm.symbol}` : undefined}
        tooltip="Excess return above the benchmark (annualized, from OLS regression)"
      />
      <KPICard
        label="Beta"
        value={beta != null ? fmtNum(beta) : "—"}
        valueClass={
          beta == null  ? "text-gray-500"
          : beta > 1.2  ? "text-amber-700"
          : beta < 0.5  ? "text-blue-700"
          : "text-gray-800"
        }
        tooltip="Sensitivity to benchmark moves. 1.0 = moves in lockstep"
      />
      <KPICard
        label="Info Ratio"
        value={infoRatio != null ? fmtNum(infoRatio) : "—"}
        valueClass={
          infoRatio == null  ? "text-gray-500"
          : infoRatio >= 0.5 ? "text-green-700"
          : infoRatio >= 0   ? "text-gray-800"
          : "text-red-600"
        }
        tooltip="Active return / tracking error. Measures quality of alpha generation"
      />
      <KPICard
        label="Cash (avg)"
        value={cashPct != null ? `${cashPct.toFixed(1)}%` : "—"}
        valueClass={
          cashPct == null  ? "text-gray-500"
          : cashPct > 25   ? "text-amber-700"
          : cashPct > 10   ? "text-gray-800"
          : "text-blue-700"
        }
        sub={am?.cash_utilization ? `${(100 - am.cash_utilization.avg_cash_pct).toFixed(1)}% deployed` : undefined}
        tooltip="Average cash allocation. Lower means more capital deployed in positions"
      />
    </div>
  );
}
