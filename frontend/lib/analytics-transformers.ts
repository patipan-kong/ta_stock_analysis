import type {
  MonthlyReturn,
  EquityCurvePoint,
  SectorContributionItem,
  PerformanceDataPoint,
} from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface HeatmapCell {
  value: number | null;
  month: number; // 1–12
}

export interface HeatmapRow {
  year: string;
  cells: HeatmapCell[]; // length 12; index 0 = Jan
  yearTotal: number | null;
}

export interface SectorBarDatum {
  sector: string;
  contribution_pct: number;
  avg_weight_pct: number;
}

export interface DecayChartDatum {
  label: string;
  avg_return_pct: number;
  sample_size: number;
}

export type DateRangeKey = "1M" | "3M" | "6M" | "YTD" | "1Y" | "ALL";

export const DATE_RANGE_OPTIONS: DateRangeKey[] = ["1M", "3M", "6M", "YTD", "1Y", "ALL"];

export const BENCHMARK_OPTIONS = [
  { label: "SET + QQQ",   value: "^SET.BK,QQQ" },
  { label: "SET Index",   value: "^SET.BK" },
  { label: "QQQ (NASDAQ-100)", value: "QQQ" },
  { label: "SPY (S&P 500)", value: "SPY" },
];

// ─── Monthly returns → heatmap matrix ────────────────────────────────────────

export const MONTH_LABELS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

export function transformMonthlyReturns(returns: MonthlyReturn[]): HeatmapRow[] {
  const map: Record<string, Record<number, number>> = {};

  for (const r of returns) {
    const [year, mStr] = r.month.split("-");
    const m = parseInt(mStr, 10) - 1; // 0-indexed
    if (!map[year]) map[year] = {};
    map[year][m] = r.return_pct;
  }

  return Object.keys(map)
    .sort()
    .map((year) => {
      const cells: HeatmapCell[] = Array.from({ length: 12 }, (_, i) => ({
        value: map[year][i] ?? null,
        month: i + 1,
      }));
      const vals = cells.filter((c) => c.value !== null).map((c) => c.value as number);
      // Compound monthly returns for year total
      const yearTotal = vals.length
        ? vals.reduce((acc, r) => acc * (1 + r / 100), 1) * 100 - 100
        : null;
      return { year, cells, yearTotal };
    });
}

// ─── Drawdown extraction from equity curve ────────────────────────────────────

export function extractDrawdownSeries(
  curve: EquityCurvePoint[],
): Array<{ date: string; drawdown_pct: number }> {
  return curve.map((p) => ({ date: p.date, drawdown_pct: p.drawdown_pct }));
}

// ─── Date range filtering ─────────────────────────────────────────────────────

export function filterByDateRange<T extends { date: string }>(
  data: T[],
  range: DateRangeKey,
): T[] {
  if (!data.length || range === "ALL") return data;
  const now = new Date();
  let cutoff: Date;
  switch (range) {
    case "1M":  cutoff = new Date(now); cutoff.setMonth(now.getMonth() - 1); break;
    case "3M":  cutoff = new Date(now); cutoff.setMonth(now.getMonth() - 3); break;
    case "6M":  cutoff = new Date(now); cutoff.setMonth(now.getMonth() - 6); break;
    case "YTD": cutoff = new Date(now.getFullYear(), 0, 1); break;
    case "1Y":  cutoff = new Date(now); cutoff.setFullYear(now.getFullYear() - 1); break;
    default:    return data;
  }
  return data.filter((d) => new Date(d.date) >= cutoff);
}

// ─── Re-normalize comparison series to base 100 after date filtering ──────────

export function rebaseToHundred(
  data: PerformanceDataPoint[],
  keys: string[],
): PerformanceDataPoint[] {
  if (!data.length) return data;
  // Base each series on its FIRST NON-NULL value — series may start later than
  // row 0 (e.g. portfolio snapshot on a weekend, benchmark prices resume Monday).
  // Using data[0] blindly would null out the entire series.
  const bases: Record<string, number> = {};
  for (const k of keys) {
    for (const row of data) {
      const v = row[k];
      if (typeof v === "number" && v !== 0) { bases[k] = v; break; }
    }
  }
  return data.map((row) => {
    const out = { date: row.date } as PerformanceDataPoint;
    for (const k of keys) {
      const v = row[k];
      if (typeof v !== "number") { out[k] = null; continue; }
      out[k] = bases[k] != null ? (v / bases[k]) * 100 : null;
    }
    return out;
  });
}

// ─── Sector contribution → recharts BarChart ─────────────────────────────────

export function transformSectorContribution(items: SectorContributionItem[]): SectorBarDatum[] {
  return [...items]
    .sort((a, b) => b.contribution_pct - a.contribution_pct)
    .map(({ sector, contribution_pct, avg_weight_pct }) => ({
      sector,
      contribution_pct,
      avg_weight_pct,
    }));
}

// ─── Signal decay → recharts BarChart ────────────────────────────────────────

export function transformSignalDecay(
  buckets: Array<{ days: number; avg_return_pct: number; sample_size: number }>,
): DecayChartDatum[] {
  return buckets.map((b) => ({
    label: `${b.days}d`,
    avg_return_pct: b.avg_return_pct,
    sample_size: b.sample_size,
  }));
}

// ─── Heatmap cell color ───────────────────────────────────────────────────────

export function returnCellStyle(pct: number | null): { bg: string; text: string } {
  if (pct === null) return { bg: "#f9fafb", text: "#9ca3af" };
  if (pct >  5)  return { bg: "#14532d", text: "#ffffff" };
  if (pct >  2)  return { bg: "#16a34a", text: "#ffffff" };
  if (pct >  0)  return { bg: "#bbf7d0", text: "#166534" };
  if (pct > -2)  return { bg: "#fecaca", text: "#991b1b" };
  if (pct > -5)  return { bg: "#dc2626", text: "#ffffff" };
  return { bg: "#7f1d1d", text: "#ffffff" };
}

// ─── Shared formatting helpers ────────────────────────────────────────────────

export function fmtPct(n: number | null | undefined, showSign = true): string {
  if (n == null) return "—";
  const sign = showSign && n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

export function fmtNum(n: number | null | undefined, decimals = 2): string {
  if (n == null) return "—";
  return n.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function pnlColorClass(n: number | null | undefined): string {
  if (n == null) return "text-gray-500";
  return n >= 0 ? "text-green-700" : "text-red-600";
}
