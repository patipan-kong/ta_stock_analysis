"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import SignalBadge from "@/components/SignalBadge";
import AnalyzeAllButton from "@/components/AnalyzeAllButton";
import TransactionModal from "@/components/TransactionModal";
import { getWatchlist, addToWatchlist, removeFromWatchlist, buyTransaction } from "@/lib/api";
import type { WatchlistItem, AnalyzeAllResult, RiskLevel, BuyPayload, TransactionResult } from "@/lib/api";
import { sectorColor } from "@/lib/sectors";
import { usePortfolio } from "@/lib/PortfolioContext";

const TZ = "Asia/Bangkok";

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("th-TH", { day: "2-digit", month: "short", year: "2-digit", timeZone: TZ }) +
    " " + d.toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit", timeZone: TZ });
}

function freshnessColor(analyzedAt: string | null): string {
  if (!analyzedAt) return "bg-red-400";
  const ageMins = (Date.now() - new Date(analyzedAt).getTime()) / 60000;
  if (ageMins <= 60) return "bg-green-400";
  if (ageMins <= 180) return "bg-yellow-400";
  return "bg-red-400";
}
function freshnessTitle(analyzedAt: string | null): string {
  if (!analyzedAt) return "Never analyzed";
  const ageMins = (Date.now() - new Date(analyzedAt).getTime()) / 60000;
  if (ageMins <= 60) return "Fresh (< 1h)";
  if (ageMins <= 180) return "1–3 hours ago";
  return "Stale (> 3h)";
}

const SIGNAL_PRIORITY: Record<string, number> = {
  BUY: 0, ACCUMULATE: 1, WATCH: 2, HOLD: 3, REDUCE: 4, SELL: 5,
};
const RISK_PRIORITY: Record<RiskLevel, number> = {
  Low: 0, Medium: 1, High: 2, Critical: 3,
};
const RISK_COLOR: Record<RiskLevel, string> = {
  Low: "#3B6D11", Medium: "#BA7517", High: "#A32D2D", Critical: "#501313",
};

function SectorBadge({ sector }: { sector?: string | null }) {
  if (!sector || sector === "Other") return <span className="text-gray-400 text-xs">{sector ?? "—"}</span>;
  const color = sectorColor(sector);
  return (
    <span
      className="inline-block text-xs font-semibold px-1.5 py-0.5 rounded whitespace-nowrap"
      style={{ color, backgroundColor: `${color}20`, border: `1px solid ${color}60` }}
    >
      {sector}
    </span>
  );
}

type SortKey = "symbol" | "sector" | "signal" | "upside_pct" | "risk_level" | "analyzed_at";
type SortDir = "asc" | "desc";

const DEFAULT_SORT: SortKey = "signal";
const DEFAULT_DIR: SortDir = "asc";

function compare(a: WatchlistItem, b: WatchlistItem, key: SortKey, dir: SortDir): number {
  let v = 0;
  switch (key) {
    case "symbol":
      v = a.symbol.localeCompare(b.symbol);
      break;
    case "signal": {
      const pa = SIGNAL_PRIORITY[a.latest_signal ?? ""] ?? 99;
      const pb = SIGNAL_PRIORITY[b.latest_signal ?? ""] ?? 99;
      // tie-break by upside DESC
      v = pa !== pb ? pa - pb : (b.upside_pct ?? -Infinity) - (a.upside_pct ?? -Infinity);
      break;
    }
    case "upside_pct":
      v = (a.upside_pct ?? -Infinity) - (b.upside_pct ?? -Infinity);
      break;
    case "sector":
      v = (a.sector ?? "Other").localeCompare(b.sector ?? "Other");
      break;
    case "risk_level": {
      const ra = RISK_PRIORITY[a.risk_level as RiskLevel] ?? -1;
      const rb = RISK_PRIORITY[b.risk_level as RiskLevel] ?? -1;
      v = ra - rb;
      break;
    }
    case "analyzed_at":
      v = (a.analyzed_at ?? "").localeCompare(b.analyzed_at ?? "");
      break;
  }
  // signal uses its own tie-break direction; other keys flip on dir
  if (key === "signal") return v;
  return dir === "asc" ? v : -v;
}

function SortIcon({ col, sortKey, sortDir }: { col: SortKey; sortKey: SortKey; sortDir: SortDir }) {
  if (col !== sortKey) return <span className="ml-0.5 text-gray-300">↕</span>;
  return <span className="ml-0.5">{sortDir === "asc" ? "↑" : "↓"}</span>;
}

function UpsideCell({ value, isDr, parentSymbol }: { value: number | null; isDr?: boolean; parentSymbol?: string | null }) {
  if (value == null) return <span className="text-gray-400 text-xs">N/A</span>;
  const color = value > 0 ? "text-green-600" : "text-red-500";
  return (
    <span className="inline-flex items-center gap-0.5 flex-wrap">
      <span className={`text-sm font-medium ${color}`}>{value > 0 ? "+" : ""}{value.toFixed(1)}%</span>
      {isDr && parentSymbol && (
        <span
          title="Upside calculated using parent stock price"
          className="text-xs font-semibold px-1 py-0.5 rounded border border-blue-300 text-blue-600 bg-blue-50 whitespace-nowrap cursor-help"
        >
          DR → {parentSymbol}
        </span>
      )}
    </span>
  );
}

function RiskBadge({ level }: { level: RiskLevel | null }) {
  if (!level) return <span className="text-gray-300 text-xs">—</span>;
  const color = RISK_COLOR[level];
  return (
    <span
      className="inline-block text-xs font-bold px-1.5 py-0.5 rounded border"
      style={{ color, borderColor: color, backgroundColor: `${color}18` }}
    >
      {level}
    </span>
  );
}

export default function WatchlistPage() {
  const { activeId: activePortfolioId } = usePortfolio();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [symbol, setSymbol] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>(DEFAULT_SORT);
  const [sortDir, setSortDir] = useState<SortDir>(DEFAULT_DIR);
  const [sectorFilter, setSectorFilter] = useState("");
  const [buyTarget, setBuyTarget] = useState<WatchlistItem | null>(null);

  useEffect(() => {
    getWatchlist().then(setItems).finally(() => setLoading(false));
  }, []);

  function handleSort(col: SortKey) {
    if (col === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(col);
      // Natural default direction per column
      setSortDir(col === "analyzed_at" ? "desc" : "asc");
    }
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const item = await addToWatchlist(symbol.trim().toUpperCase());
      setItems((prev) => [...prev, item]);
      setSymbol("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add");
    }
  }

  async function handleRemove(sym: string) {
    await removeFromWatchlist(sym);
    setItems((prev) => prev.filter((i) => i.symbol !== sym));
  }

  async function handleAnalyzeAllComplete(_result: AnalyzeAllResult) {
    const updated = await getWatchlist();
    setItems(updated);
  }

  const staleCount = items.filter((i) => {
    if (!i.analyzed_at) return true;
    return (Date.now() - new Date(i.analyzed_at).getTime()) / 60000 > 60;
  }).length;

  const sectorCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const item of items) {
      const s = item.sector ?? "Other";
      counts[s] = (counts[s] ?? 0) + 1;
    }
    return counts;
  }, [items]);

  const sorted = useMemo(() => {
    const base = sectorFilter ? items.filter((i) => (i.sector ?? "Other") === sectorFilter) : items;
    return [...base].sort((a, b) => compare(a, b, sortKey, sortDir));
  }, [items, sectorFilter, sortKey, sortDir]);

  function Th({ col, label, className }: { col: SortKey; label: string; className?: string }) {
    const active = col === sortKey;
    return (
      <th
        className={`py-2 pr-3 font-medium cursor-pointer select-none whitespace-nowrap hover:text-gray-800 transition-colors ${active ? "text-gray-700" : "text-gray-400"} ${className ?? ""}`}
        onClick={() => handleSort(col)}
      >
        {label}<SortIcon col={col} sortKey={sortKey} sortDir={sortDir} />
      </th>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h1 className="text-2xl font-bold">Watchlist</h1>
        {items.length > 0 && (
          <AnalyzeAllButton
            type="watchlist"
            staleCount={staleCount}
            totalCount={items.length}
            onComplete={handleAnalyzeAllComplete}
          />
        )}
      </div>

      <form onSubmit={handleAdd} className="flex gap-3 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Symbol</label>
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder="TSLA or PTT.BK"
            required
            className="border rounded px-3 py-1.5 text-sm w-36"
          />
        </div>
        <button type="submit" className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm hover:bg-blue-700">
          Watch
        </button>
        {error && <p className="text-red-500 text-xs self-center">{error}</p>}
      </form>

      {loading ? (
        <p className="text-sm text-gray-400">Loading…</p>
      ) : sorted.length === 0 && !sectorFilter ? (
        <p className="text-sm text-gray-500">Watchlist is empty.</p>
      ) : (
        <>
        {Object.keys(sectorCounts).length > 1 && (
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-500 shrink-0">Sector</label>
            <select
              value={sectorFilter}
              onChange={(e) => setSectorFilter(e.target.value)}
              className="text-sm border rounded px-2.5 py-1.5 bg-white"
            >
              <option value="">All Sectors ({items.length})</option>
              {Object.entries(sectorCounts)
                .sort((a, b) => b[1] - a[1])
                .map(([sector, count]) => (
                  <option key={sector} value={sector}>{sector} ({count})</option>
                ))}
            </select>
            {sectorFilter && (
              <button onClick={() => setSectorFilter("")} className="text-xs text-gray-400 hover:text-gray-600">✕ Clear</button>
            )}
          </div>
        )}
        {sorted.length === 0 ? (
          <p className="text-sm text-gray-500">No stocks in &quot;{sectorFilter}&quot; sector.</p>
        ) : (
        <div className="bg-white border rounded-xl overflow-x-auto shadow-sm">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs">
                <Th col="symbol"      label="Symbol"   className="pl-4" />
                <Th col="sector" label="Sector" />
                <Th col="signal"      label="Signal" />
                <Th col="upside_pct"  label="Upside" />
                <Th col="risk_level"  label="Risk" />
                <Th col="analyzed_at" label="Analyzed"  className="hidden sm:table-cell" />
                <th className="py-2 pr-4 text-right text-gray-400 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((item) => {
                const display = item.symbol.replace(".BK", "");
                return (
                  <tr key={item.symbol} className="border-b hover:bg-gray-50">
                    <td className="py-2.5 pl-4 pr-3 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <Link href={`/stock/${encodeURIComponent(item.symbol)}`}>
                          <span
                            className={`inline-block w-2 h-2 rounded-full shrink-0 ${freshnessColor(item.analyzed_at)} hover:scale-125 transition-transform`}
                            title={freshnessTitle(item.analyzed_at)}
                          />
                        </Link>
                        <Link href={`/stock/${encodeURIComponent(item.symbol)}`} className="text-blue-600 hover:underline font-medium">
                          {display}
                          {item.symbol.endsWith(".BK") && <span className="ml-1 text-xs text-gray-400">.BK</span>}
                        </Link>
                      </div>
                    </td>
                    <td className="py-2.5 pr-3"><SectorBadge sector={item.sector} /></td>
                    <td className="py-2.5 pr-3">
                      {item.latest_signal
                        ? <SignalBadge signal={item.latest_signal} />
                        : <span className="text-xs text-gray-400">—</span>}
                    </td>
                    <td className="py-2.5 pr-3"><UpsideCell value={item.upside_pct} isDr={item.is_dr} parentSymbol={item.parent_symbol} /></td>
                    <td className="py-2.5 pr-3"><RiskBadge level={item.risk_level} /></td>
                    <td className="py-2.5 pr-3 text-xs text-gray-400 hidden sm:table-cell">{formatDate(item.analyzed_at)}</td>
                    <td className="py-2.5 pr-4">
                      <div className="flex items-center justify-end gap-2">
                        {activePortfolioId != null && (
                          <button
                            onClick={() => setBuyTarget(item)}
                            className="text-xs font-semibold px-2 py-0.5 rounded border transition-colors"
                            style={{ color: "#27500A", borderColor: "#27500A60", backgroundColor: "#27500A10" }}
                            title="Buy into active portfolio"
                          >
                            Buy
                          </button>
                        )}
                        <button onClick={() => handleRemove(item.symbol)} className="text-red-500 hover:text-red-700 text-xs">
                          Remove
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        )}
        </>
      )}

      {buyTarget != null && activePortfolioId != null && (
        <TransactionModal
          mode="buy"
          symbol={buyTarget.symbol}
          onConfirm={(payload) => buyTransaction(activePortfolioId, payload as BuyPayload)}
          onClose={() => setBuyTarget(null)}
        />
      )}
    </div>
  );
}
