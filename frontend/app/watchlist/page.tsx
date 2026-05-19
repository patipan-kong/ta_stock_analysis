"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import SignalBadge from "@/components/SignalBadge";
import AnalyzeAllButton from "@/components/AnalyzeAllButton";
import { getWatchlist, addToWatchlist, removeFromWatchlist } from "@/lib/api";
import type { WatchlistItem, AnalyzeAllResult } from "@/lib/api";

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

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [symbol, setSymbol] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getWatchlist().then(setItems).finally(() => setLoading(false));
  }, []);

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
      ) : items.length === 0 ? (
        <p className="text-sm text-gray-500">Watchlist is empty.</p>
      ) : (
        <ul className="divide-y">
          {items.map((item) => {
            const display = item.symbol.replace(".BK", "");
            return (
              <li key={item.symbol} className="py-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 min-w-0">
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
                  {item.latest_signal
                    ? <SignalBadge signal={item.latest_signal} />
                    : <span className="text-xs text-gray-400">—</span>}
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-xs text-gray-400 hidden sm:block">{formatDate(item.analyzed_at)}</span>
                  <button
                    onClick={() => handleRemove(item.symbol)}
                    className="text-red-500 hover:text-red-700 text-xs"
                  >
                    Remove
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
