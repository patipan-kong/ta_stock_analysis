"use client";

import { useEffect, useState, useCallback } from "react";
import {
  ComposedChart, LineChart, Bar, Cell,
  Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import { getStockChart } from "@/lib/api";
import type { ChartCandle } from "@/lib/api";

const TZ = "Asia/Bangkok";

const PERIODS = [
  { label: "1D",  period: "1d",  interval: "5m"  },
  { label: "5D",  period: "5d",  interval: "30m" },
  { label: "1M",  period: "1mo", interval: "1d"  },
  { label: "3M",  period: "3mo", interval: "1d"  },
  { label: "1Y",  period: "1y",  interval: "1wk" },
  { label: "3Y",  period: "3y",  interval: "1wk" },
] as const;

const DEFAULT_PERIOD_IDX = 4; // 1Y

type IndicatorTab = "macd" | "rsi";

function formatAxisTime(iso: string, period: string): string {
  const d = new Date(iso);
  if (period === "1d") return d.toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit", timeZone: TZ });
  if (period === "5d") return d.toLocaleDateString("th-TH", { weekday: "short", day: "2-digit", timeZone: TZ });
  return d.toLocaleDateString("th-TH", { day: "2-digit", month: "short", timeZone: TZ });
}

function formatTooltipTime(iso: string, period: string): string {
  const d = new Date(iso);
  if (period === "1d") return d.toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit", timeZone: TZ });
  return (
    d.toLocaleDateString("th-TH", { day: "2-digit", month: "short", year: "2-digit", timeZone: TZ }) +
    " " + d.toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit", timeZone: TZ })
  );
}

function tickEvery(candles: ChartCandle[], target = 8): string[] {
  if (!candles.length) return [];
  const step = Math.max(1, Math.floor(candles.length / target));
  return candles.filter((_, i) => i % step === 0).map((c) => c.time);
}

const PRICE_CLR   = "#3b82f6";
const EMA_CLR     = "#f97316";
const TEMA_CLR    = "#06b6d4";
const ZIGZAG_CLR  = "#ec4899";
const BB_CLR      = "#9ca3af";
const RSI_CLR     = "#8b5cf6";
const MACD_CLR    = "#3b82f6";
const SIG_CLR     = "#f97316";
const HIST_POS    = "#86efac";
const HIST_NEG    = "#fca5a5";

// ─── Tooltips ────────────────────────────────────────────────────────────────

function PriceTooltip({ active, payload, label, period }: {
  active?: boolean; payload?: Array<{ name: string; value: number | null }>; label?: string; period: string;
}) {
  if (!active || !payload?.length || !label) return null;
  const m = Object.fromEntries(payload.map((p) => [p.name, p.value]));
  return (
    <div className="bg-white border border-gray-200 rounded-lg px-3 py-2 text-xs shadow-lg space-y-0.5">
      <p className="font-medium text-gray-500 mb-1">{formatTooltipTime(label, period)}</p>
      {m.close    != null && <p className="text-blue-600 font-semibold">Close: {Number(m.close).toFixed(2)}</p>}
      {m.ema20    != null && <p className="text-orange-500">EMA20: {Number(m.ema20).toFixed(2)}</p>}
      {m.tema9    != null && <p className="text-cyan-500">TEMA9: {Number(m.tema9).toFixed(2)}</p>}
      {m.zigzag   != null && <p className="text-pink-500">ZigZag: {Number(m.zigzag).toFixed(2)}</p>}
      {m.bb_upper != null && <p className="text-gray-400">BB↑: {Number(m.bb_upper).toFixed(2)}</p>}
      {m.bb_lower != null && <p className="text-gray-400">BB↓: {Number(m.bb_lower).toFixed(2)}</p>}
    </div>
  );
}

function MACDTooltip({ active, payload, label, period }: {
  active?: boolean; payload?: Array<{ name: string; value: number | null }>; label?: string; period: string;
}) {
  if (!active || !payload?.length || !label) return null;
  const m = Object.fromEntries(payload.map((p) => [p.name, p.value]));
  return (
    <div className="bg-white border border-gray-200 rounded-lg px-2 py-1.5 text-xs shadow-lg space-y-0.5">
      {m.macd_line   != null && <p className="text-blue-600">MACD: {Number(m.macd_line).toFixed(4)}</p>}
      {m.macd_signal != null && <p className="text-orange-500">Signal: {Number(m.macd_signal).toFixed(4)}</p>}
      {m.macd_hist   != null && (
        <p className={Number(m.macd_hist) >= 0 ? "text-green-600" : "text-red-500"}>
          Hist: {Number(m.macd_hist).toFixed(4)}
        </p>
      )}
    </div>
  );
}

function RSITooltip({ active, payload }: { active?: boolean; payload?: Array<{ value: number | null }> }) {
  if (!active || !payload?.length) return null;
  const rsi = payload[0]?.value;
  return (
    <div className="bg-white border border-gray-200 rounded-lg px-2 py-1 text-xs shadow-lg">
      <p className="text-violet-600 font-semibold">RSI: {rsi != null ? Number(rsi).toFixed(1) : "—"}</p>
    </div>
  );
}

// ─── Chart component ─────────────────────────────────────────────────────────

export default function StockChart({ symbol }: { symbol: string }) {
  const [periodIdx, setPeriodIdx] = useState(DEFAULT_PERIOD_IDX);
  const [indicator, setIndicator] = useState<IndicatorTab>("macd");
  const [candles, setCandles] = useState<ChartCandle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const { period, interval } = PERIODS[periodIdx];

  const loadChart = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getStockChart(symbol, period, interval);
      if (data.error) { setError(data.error); setCandles([]); }
      else setCandles(data.candles.filter((c) => c.close != null));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load chart");
    } finally {
      setLoading(false);
    }
  }, [symbol, period, interval]);

  useEffect(() => { loadChart(); }, [loadChart]);

  const ticks = tickEvery(candles);

  const allY = [
    ...candles.map((c) => c.close),
    ...candles.map((c) => c.bb_upper),
    ...candles.map((c) => c.bb_lower),
    ...candles.map((c) => c.zigzag),
  ].filter((v): v is number => v != null);
  const yMin = allY.length ? Math.min(...allY) : 0;
  const yMax = allY.length ? Math.max(...allY) : 1;
  const yPad = (yMax - yMin) * 0.04;

  return (
    <div className="space-y-1">
      {/* ── Controls row ── */}
      <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
        <div className="flex items-center gap-0.5">
          {PERIODS.map((p, i) => (
            <button
              key={p.label}
              onClick={() => setPeriodIdx(i)}
              className={`text-xs px-2.5 py-1 rounded-md font-medium transition-colors ${
                i === periodIdx ? "bg-blue-600 text-white" : "text-gray-500 hover:bg-gray-100"
              }`}
            >
              {p.label}
            </button>
          ))}
          {loading && <span className="text-xs text-gray-400 ml-2">Loading…</span>}
        </div>

        <div className="flex items-center gap-0.5 bg-gray-100 rounded-md p-0.5">
          {(["macd", "rsi"] as IndicatorTab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setIndicator(tab)}
              className={`text-xs px-2.5 py-0.5 rounded font-medium transition-colors uppercase ${
                indicator === tab ? "bg-white text-gray-800 shadow-sm" : "text-gray-400 hover:text-gray-600"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {error ? (
        <p className="text-xs text-gray-400 py-8 text-center">{error}</p>
      ) : (
        <>
          {/* ── Price + BB + EMA + TEMA + ZigZag panel ── */}
          <ResponsiveContainer width="100%" height={260}>
            <ComposedChart data={candles} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
              <XAxis
                dataKey="time"
                ticks={ticks}
                tickFormatter={(v) => formatAxisTime(v, period)}
                tick={{ fontSize: 10, fill: "#9ca3af" }}
                axisLine={false} tickLine={false}
              />
              <YAxis
                domain={[yMin - yPad, yMax + yPad]}
                tick={{ fontSize: 10, fill: "#9ca3af" }}
                axisLine={false} tickLine={false}
                width={54}
                tickFormatter={(v) => v.toFixed(1)}
              />
              <Tooltip content={<PriceTooltip period={period} />} />
              <Line dataKey="bb_upper"  stroke={BB_CLR}      strokeWidth={1}   strokeDasharray="4 3" dot={false} name="bb_upper"  connectNulls />
              <Line dataKey="bb_middle" stroke={BB_CLR}      strokeWidth={1}   strokeDasharray="2 4" dot={false} name="bb_middle" connectNulls strokeOpacity={0.4} />
              <Line dataKey="bb_lower"  stroke={BB_CLR}      strokeWidth={1}   strokeDasharray="4 3" dot={false} name="bb_lower"  connectNulls />
              <Line dataKey="ema20"     stroke={EMA_CLR}     strokeWidth={1.5} strokeDasharray="5 2" dot={false} name="ema20"     connectNulls />
              <Line dataKey="tema9"     stroke={TEMA_CLR}    strokeWidth={1.5} strokeDasharray="3 2" dot={false} name="tema9"     connectNulls />
              <Line dataKey="zigzag"    stroke={ZIGZAG_CLR}  strokeWidth={2}   dot={false}           name="zigzag"    connectNulls />
              <Line dataKey="close"     stroke={PRICE_CLR}   strokeWidth={2}   dot={false}           name="close"     connectNulls />
            </ComposedChart>
          </ResponsiveContainer>

          {/* Legend */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-1 text-xs text-gray-400 mb-1">
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-5 border-t-2 border-blue-500" />Price
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-5 border-t-2 border-dashed border-orange-400" />EMA20
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-5 border-t-2 border-dashed border-cyan-400" />TEMA9
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-5 border-t-2 border-pink-400" />ZigZag(5,10)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-5 border-t border-dashed border-gray-300" />BB Bands
            </span>
          </div>

          {/* ── Indicator panel ── */}
          {indicator === "macd" ? (
            <div>
              <p className="text-xs text-gray-400 px-1 mb-1">MACD EMA(12, 26, 9) — close</p>
              <ResponsiveContainer width="100%" height={90}>
                <ComposedChart data={candles} margin={{ top: 2, right: 4, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
                  <XAxis dataKey="time" hide />
                  <YAxis
                    tick={{ fontSize: 9, fill: "#9ca3af" }}
                    axisLine={false} tickLine={false}
                    width={42}
                    tickFormatter={(v) => v.toFixed(3)}
                  />
                  <Tooltip content={<MACDTooltip period={period} />} />
                  <ReferenceLine y={0} stroke="#e5e7eb" strokeWidth={1} />
                  <Bar dataKey="macd_hist" name="macd_hist" isAnimationActive={false}>
                    {candles.map((c, i) => (
                      <Cell key={i} fill={(c.macd_hist ?? 0) >= 0 ? HIST_POS : HIST_NEG} />
                    ))}
                  </Bar>
                  <Line dataKey="macd_line"   stroke={MACD_CLR} strokeWidth={1.5} dot={false} name="macd_line"   connectNulls />
                  <Line dataKey="macd_signal" stroke={SIG_CLR}  strokeWidth={1.5} strokeDasharray="4 2" dot={false} name="macd_signal" connectNulls />
                </ComposedChart>
              </ResponsiveContainer>
              <div className="flex items-center gap-4 px-1 mt-0.5 text-xs text-gray-400">
                <span className="flex items-center gap-1.5"><span className="inline-block w-5 border-t-2 border-blue-500" />MACD</span>
                <span className="flex items-center gap-1.5"><span className="inline-block w-5 border-t-2 border-dashed border-orange-400" />Signal</span>
                <span className="flex items-center gap-1.5"><span className="inline-block w-3 h-2.5 rounded-sm bg-green-200" /><span className="inline-block w-3 h-2.5 rounded-sm bg-red-200 ml-0.5" />Hist</span>
              </div>
            </div>
          ) : (
            <div>
              <p className="text-xs text-gray-400 px-1 mb-1">RSI (14)</p>
              <ResponsiveContainer width="100%" height={80}>
                <LineChart data={candles} margin={{ top: 2, right: 4, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
                  <XAxis dataKey="time" hide />
                  <YAxis
                    domain={[0, 100]}
                    ticks={[30, 50, 70]}
                    tick={{ fontSize: 9, fill: "#9ca3af" }}
                    axisLine={false} tickLine={false}
                    width={28}
                  />
                  <Tooltip content={<RSITooltip />} />
                  <ReferenceLine y={70} stroke="#fca5a5" strokeDasharray="3 3" strokeWidth={1} />
                  <ReferenceLine y={30} stroke="#86efac" strokeDasharray="3 3" strokeWidth={1} />
                  <ReferenceLine y={50} stroke="#e5e7eb" strokeWidth={1} />
                  <Line dataKey="rsi" stroke={RSI_CLR} strokeWidth={1.5} dot={false} connectNulls />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  );
}
