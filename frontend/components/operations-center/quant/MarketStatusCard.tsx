"use client";

import type { OperationsMarket } from "@/lib/api";
import { marketDataFreshnessTh, isMarketDataStale } from "../freshness";

const REGIME_CFG: Record<string, { bg: string; border: string; text: string }> = {
  RISK_ON:            { bg: "bg-emerald-50", border: "border-emerald-300", text: "text-emerald-700" },
  RISK_OFF:           { bg: "bg-red-50",     border: "border-red-300",     text: "text-red-700" },
  SIDEWAYS:           { bg: "bg-gray-50",    border: "border-gray-300",    text: "text-gray-700" },
  HIGH_VOLATILITY:    { bg: "bg-orange-50",  border: "border-orange-300",  text: "text-orange-700" },
  DEFENSIVE_REGIME:   { bg: "bg-blue-50",    border: "border-blue-300",    text: "text-blue-700" },
  TRANSITION_RISK_ON: { bg: "bg-teal-50",    border: "border-teal-300",    text: "text-teal-700" },
  TRANSITION_RISK_OFF:{ bg: "bg-amber-50",   border: "border-amber-300",   text: "text-amber-700" },
};
const DEFAULT_CFG = { bg: "bg-gray-50", border: "border-gray-300", text: "text-gray-500" };

export default function MarketStatusCard({
  market,
  snapshotDate,
}: {
  market: OperationsMarket;
  snapshotDate: string | null;
}) {
  const cfg = market.regime ? (REGIME_CFG[market.regime] ?? DEFAULT_CFG) : DEFAULT_CFG;
  const stale = isMarketDataStale(snapshotDate);
  const freshnessLabel = marketDataFreshnessTh(snapshotDate);

  return (
    <div className={`rounded-2xl border-2 ${cfg.border} ${cfg.bg} p-5 space-y-3 shadow-sm`}>
      <div className="flex items-center justify-between flex-wrap gap-2">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
          สถานะตลาด
        </p>
        <div className="flex items-center gap-2">
          {stale && (
            <span className="text-[10px] font-semibold text-amber-700 bg-amber-50 border border-amber-300 rounded-full px-2 py-0.5">
              ⚠ ข้อมูลอาจไม่เป็นปัจจุบัน
            </span>
          )}
          {market.transition_stability && (
            <span className="font-mono text-[10px] font-bold text-gray-500 border border-gray-300 bg-white px-2 py-0.5 rounded-full">
              {market.transition_stability}
            </span>
          )}
        </div>
      </div>

      {market.regime ? (
        <p className={`text-2xl font-bold ${cfg.text}`}>{market.label_th || market.regime}</p>
      ) : (
        <p className="text-sm text-gray-400">ยังไม่มีข้อมูลสภาวะตลาด</p>
      )}

      <div className="grid grid-cols-3 gap-3 bg-white/60 rounded-xl p-3 text-center">
        <div>
          <p className="text-[10px] text-gray-400 uppercase">ความเชื่อมั่น</p>
          <p className="text-sm font-bold text-gray-800">
            {market.confidence_pct != null ? `${market.confidence_pct.toFixed(0)}%` : "—"}
          </p>
        </div>
        <div>
          <p className="text-[10px] text-gray-400 uppercase">VIX</p>
          <p className="text-sm font-bold text-gray-800">
            {market.vix_level != null ? market.vix_level.toFixed(1) : "—"}
          </p>
        </div>
        <div>
          <p className="text-[10px] text-gray-400 uppercase">ระยะเวลา</p>
          <p className="text-sm font-bold text-gray-800">
            {market.regime_duration_days != null ? `${market.regime_duration_days} วัน` : "—"}
          </p>
        </div>
      </div>

      {market.narrative && (
        <p className="text-xs text-gray-600 leading-relaxed">{market.narrative}</p>
      )}

      <p className="text-[11px] text-gray-400">{freshnessLabel}</p>
    </div>
  );
}
