import type { PortfolioItem } from "@/lib/api";

function fmt(n: number): string {
  return n.toLocaleString("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function StatCard({
  label,
  value,
  sub,
  positive,
}: {
  label: string;
  value: string;
  sub?: string;
  positive?: boolean | null;
}) {
  const valueColor =
    positive === true
      ? "text-green-600"
      : positive === false
      ? "text-red-600"
      : "text-gray-800";
  return (
    <div className="bg-white border rounded-xl p-3 text-center shadow-sm">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className={`text-base font-bold ${valueColor}`}>{value}</p>
      {sub && <p className={`text-xs mt-0.5 ${valueColor}`}>{sub}</p>}
    </div>
  );
}

export default function PortfolioSummary({
  items,
  cashBalance,
}: {
  items: PortfolioItem[];
  cashBalance: number;
}) {
  const totalCost = items.reduce((s, i) => s + i.shares * i.avg_cost, 0);
  const stockValue = items.reduce(
    (s, i) => s + i.shares * (i.current_price ?? i.avg_cost),
    0
  );
  const portfolioValue = stockValue + cashBalance;
  const pl = stockValue - totalCost;
  const plPct = totalCost > 0 ? (pl / totalCost) * 100 : 0;
  const plPositive = pl > 0 ? true : pl < 0 ? false : null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <StatCard label="Total Cost" value={fmt(totalCost)} />
      <StatCard label="Market Value" value={fmt(portfolioValue)} />
      <StatCard
        label="P/L"
        value={(pl >= 0 ? "+" : "") + fmt(pl)}
        positive={plPositive}
      />
      <StatCard
        label="%P/L"
        value={(plPct >= 0 ? "+" : "") + plPct.toFixed(2) + "%"}
        positive={plPositive}
      />
    </div>
  );
}
