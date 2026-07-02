"use client";

import type { PortfolioAnalyticsMetrics, AllocationAnalyticsMetrics } from "@/lib/api";
import { fmtPct, fmtNum, pnlColorClass } from "@/lib/analytics-transformers";
import { KPICard, SkeletonCard } from "./KPICard";

interface PortfolioPerformanceGridProps {
  portfolioMetrics: PortfolioAnalyticsMetrics | null;
  allocationMetrics: AllocationAnalyticsMetrics | null;
  loading?: boolean;
}

export default function PortfolioPerformanceGrid({
  portfolioMetrics: pm,
  allocationMetrics: am,
  loading,
}: PortfolioPerformanceGridProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {Array.from({ length: 7 }).map((_, i) => <SkeletonCard key={i} />)}
      </div>
    );
  }

  const MIN_DAYS_FOR_ANN = 30;
  const spanDays = pm?.date_range?.from && pm?.date_range?.to
    ? Math.floor((new Date(pm.date_range.to).getTime() - new Date(pm.date_range.from).getTime()) / 86_400_000)
    : null;
  const collecting = (metric: number | null) =>
    metric == null && spanDays != null && spanDays < MIN_DAYS_FOR_ANN;
  const collectingLabel = spanDays != null
    ? `Collecting Data (${spanDays}/${MIN_DAYS_FOR_ANN} days)`
    : "—";

  const totalReturn = pm?.cumulative_return_pct ?? null;
  const annReturn   = pm?.annualized_return_pct ?? null;
  const maxDd       = pm?.max_drawdown?.max_drawdown_pct ?? null;
  const vol         = pm?.volatility_pct ?? null;
  const sharpe      = pm?.sharpe_ratio ?? null;
  const winMonth    = pm?.monthly_win_rate?.win_rate ?? null;
  const cashPct     = am?.cash_utilization?.avg_cash_pct ?? null;

  const ddDays = pm?.max_drawdown?.duration_days;
  const ddSub  = ddDays != null ? `${ddDays}d recovery` : undefined;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-3">
      <KPICard
        label="Total Return"
        value={fmtPct(totalReturn)}
        valueClass={pnlColorClass(totalReturn)}
        tooltip="Cumulative portfolio return over the full snapshot history"
      />
      <KPICard
        label="Ann. Return"
        value={annReturn != null ? fmtPct(annReturn) : collectingLabel}
        valueClass={collecting(annReturn) ? "text-amber-600" : pnlColorClass(annReturn)}
        compact={collecting(annReturn)}
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
        value={vol != null ? fmtPct(vol, false) : collectingLabel}
        valueClass={collecting(vol) ? "text-amber-600" : "text-gray-800"}
        compact={collecting(vol)}
        tooltip="Annualized standard deviation of daily returns"
      />
      <KPICard
        label="Sharpe Ratio"
        value={sharpe != null ? fmtNum(sharpe) : collecting(sharpe) ? collectingLabel : "—"}
        valueClass={
          collecting(sharpe) ? "text-amber-600"
          : sharpe == null   ? "text-gray-500"
          : sharpe >= 1      ? "text-green-700"
          : sharpe >= 0      ? "text-gray-800"
          : "text-red-600"
        }
        compact={collecting(sharpe)}
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
