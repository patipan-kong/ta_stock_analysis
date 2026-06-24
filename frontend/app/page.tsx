"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePortfolio } from "@/lib/PortfolioContext";
import { getHoldings, getPortfolioPrices } from "@/lib/api";
import type { Portfolio, PortfolioItem, PriceRefreshItem } from "@/lib/api";

function heatTileColor(cp: number | null, pricesLoaded: boolean): string {
  if (!pricesLoaded) return "#374151"; // dark gray — still loading
  if (cp == null) return "#1F2937";   // near-black — confirmed no data
  if (Math.abs(cp) < 0.3) return "#4B5563"; // neutral
  const intensity = Math.min(Math.abs(cp) / 5, 1);
  if (cp > 0) {
    return `hsl(142, ${Math.round(50 + intensity * 30)}%, ${Math.round(38 - intensity * 10)}%)`;
  }
  return `hsl(0, ${Math.round(60 + intensity * 20)}%, ${Math.round(50 - intensity * 12)}%)`;
}

function DashboardHeatmap({
  holdingsMap,
  priceMap,
  pricesLoaded,
  portfolios,
}: {
  holdingsMap: Record<number, PortfolioItem[]>;
  priceMap: Record<number, PriceRefreshItem[]>;
  pricesLoaded: boolean;
  portfolios: Portfolio[];
}) {
  const aggregated = new Map<string, {
    symbol: string;
    mv: number;
    cp: number | null;
    priceConfirmed: boolean;
  }>();

  portfolios.forEach((p) => {
    const liveBySymbol = new Map((priceMap[p.id] ?? []).map((pr) => [pr.symbol, pr]));

    (holdingsMap[p.id] ?? []).forEach((item) => {
      const live = liveBySymbol.get(item.symbol);
      const price = live?.current_price ?? item.current_price ?? item.avg_cost;
      const mv = item.shares * price;
      const cp = live?.change_percent ?? null;
      const priceConfirmed = pricesLoaded && !!live;

      const existing = aggregated.get(item.symbol);
      if (existing) {
        existing.mv += mv;
        if (cp != null) existing.cp = cp;
        if (priceConfirmed) existing.priceConfirmed = true;
      } else {
        aggregated.set(item.symbol, { symbol: item.symbol, mv, cp, priceConfirmed });
      }
    });
  });

  const tiles = Array.from(aggregated.values()).sort((a, b) => b.mv - a.mv);
  if (tiles.length === 0) return null;

  const totalValue = tiles.reduce((s, t) => s + t.mv, 0);

  return (
    <section>
      <div className="flex items-center gap-3 mb-2">
        <h2 className="text-base font-semibold text-gray-500 uppercase tracking-wide">Portfolio Heatmap</h2>
        {!pricesLoaded && (
          <span className="text-xs text-gray-400 flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
            Loading prices…
          </span>
        )}
      </div>
      <div className="flex flex-wrap gap-1">
        {tiles.map((tile) => {
          const weightPct = totalValue > 0 ? (tile.mv / totalValue) * 100 : 100 / tiles.length;
          const display = tile.symbol.replace(".BK", "");

          let changeText: string;
          let changeColor: string;
          if (!pricesLoaded) {
            changeText = "…";
            changeColor = "text-gray-400";
          } else if (tile.cp == null) {
            changeText = "No price data";
            changeColor = "text-gray-500";
          } else {
            changeText = `${tile.cp > 0 ? "+" : ""}${tile.cp.toFixed(2)}%`;
            changeColor = tile.cp > 0.3 ? "text-green-200" : tile.cp < -0.3 ? "text-red-200" : "text-gray-300";
          }

          return (
            <Link
              key={tile.symbol}
              href={`/stock/${encodeURIComponent(tile.symbol)}`}
              style={{
                flexBasis: `${Math.max(6, weightPct - 0.5)}%`,
                flexGrow: 0,
                flexShrink: 1,
                background: heatTileColor(tile.cp, pricesLoaded || tile.priceConfirmed),
                minWidth: 72,
                minHeight: 72,
              }}
              className="rounded-lg p-2 flex flex-col justify-between hover:brightness-110 transition-all cursor-pointer"
            >
              <span className="text-white text-xs font-bold truncate leading-tight">{display}</span>
              <div>
                <div className={`text-xs font-semibold leading-tight ${changeColor}`}>{changeText}</div>
                <div className="text-xs text-white/50">{weightPct.toFixed(1)}%</div>
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

export default function DashboardPage() {
  const { portfolios, loading: ctxLoading } = usePortfolio();
  const [holdingsMap, setHoldingsMap] = useState<Record<number, PortfolioItem[]>>({});
  const [priceMap, setPriceMap] = useState<Record<number, PriceRefreshItem[]>>({});
  const [loadingHoldings, setLoadingHoldings] = useState(false);
  const [pricesLoaded, setPricesLoaded] = useState(false);
  const [error, setError] = useState("");

  // Phase 1: load holdings from DB (fast, no yfinance)
  useEffect(() => {
    if (ctxLoading || portfolios.length === 0) return;
    setLoadingHoldings(true);
    setPricesLoaded(false);
    Promise.all(
      portfolios.map((p) => getHoldings(p.id).then((items) => ({ id: p.id, items })))
    )
      .then((results) => {
        const map: Record<number, PortfolioItem[]> = {};
        results.forEach(({ id, items }) => { map[id] = items; });
        setHoldingsMap(map);
      })
      .catch(() => setError("Cannot connect to backend"))
      .finally(() => setLoadingHoldings(false));
  }, [portfolios, ctxLoading]);

  // Phase 2: fetch live prices once holdings are known (hits yfinance cache)
  useEffect(() => {
    if (portfolios.length === 0 || Object.keys(holdingsMap).length === 0) return;
    Promise.all(
      portfolios.map((p) => getPortfolioPrices(p.id).then((prices) => ({ id: p.id, prices })))
    )
      .then((results) => {
        const map: Record<number, PriceRefreshItem[]> = {};
        results.forEach(({ id, prices }) => { map[id] = prices; });
        setPriceMap(map);
      })
      .catch(() => {
        // prices failing is non-fatal — heatmap shows "No price data"
      })
      .finally(() => setPricesLoaded(true));
  }, [holdingsMap, portfolios]);

  const isLoading = ctxLoading || loadingHoldings;

  return (
    <div className="space-y-10">
      <section>
        <h1 className="text-2xl font-bold mb-1">Dashboard</h1>
        {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
      </section>

      {isLoading ? (
        <p className="text-sm text-gray-400">Loading…</p>
      ) : (
        <DashboardHeatmap
          holdingsMap={holdingsMap}
          priceMap={priceMap}
          pricesLoaded={pricesLoaded}
          portfolios={portfolios}
        />
      )}
    </div>
  );
}
