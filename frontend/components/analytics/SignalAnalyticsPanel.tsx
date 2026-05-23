"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import type { SignalAnalyticsMetrics } from "@/lib/api";
import { transformSignalDecay, fmtPct, fmtNum } from "@/lib/analytics-transformers";

function ProgressBar({
  value,
  max = 100,
  color = "#2563eb",
  label,
}: {
  value: number;
  max?: number;
  color?: string;
  label?: string;
}) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      {label && <span className="text-xs font-semibold text-gray-700 w-12 text-right tabular-nums">{label}</span>}
    </div>
  );
}

function MetricRow({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="flex items-start justify-between py-2 border-b border-gray-50 last:border-0">
      <span className="text-xs text-gray-500">{label}</span>
      <div className="text-right">
        <span className="text-sm font-semibold text-gray-800 tabular-nums">{value}</span>
        {sub && <p className="text-xs text-gray-400">{sub}</p>}
      </div>
    </div>
  );
}

function ConfidenceBadge({ n }: { n: number }) {
  const cls =
    n >= 30  ? "bg-green-100 text-green-700" :
    n >= 10  ? "bg-amber-100 text-amber-700" :
               "bg-gray-100 text-gray-500";
  const label = n >= 30 ? "High confidence" : n >= 10 ? "Moderate" : "Low sample";
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>
      {label} (n={n})
    </span>
  );
}

interface SignalAnalyticsPanelProps {
  metrics: SignalAnalyticsMetrics | null;
}

export default function SignalAnalyticsPanel({ metrics }: SignalAnalyticsPanelProps) {
  if (!metrics || metrics.total_signals === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-sm text-gray-400">
        No signal history yet. Run the optimizer to generate signals.
      </div>
    );
  }

  const { buy_win_rate, sell_accuracy, average_holding_return, signal_decay, signals_by_action } = metrics;

  const decayData = transformSignalDecay(signal_decay?.buckets ?? []);

  const signalDistribution = Object.entries(signals_by_action ?? {})
    .sort((a, b) => b[1] - a[1]);

  const ACTION_COLORS: Record<string, string> = {
    BUY:        "#27500A",
    ACCUMULATE: "#0F6E56",
    HOLD:       "#444441",
    REDUCE:     "#854F0B",
    SELL:       "#791F1F",
  };

  return (
    <div className="space-y-5">
      {/* Win rate section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-700">Buy Signal Win Rate</h3>
          <ConfidenceBadge n={buy_win_rate?.total ?? 0} />
        </div>
        <div className="flex items-end gap-3 mb-2">
          <span className="text-2xl font-bold text-green-700">
            {buy_win_rate?.win_rate != null ? `${buy_win_rate.win_rate.toFixed(1)}%` : "—"}
          </span>
          <span className="text-xs text-gray-400 mb-1">
            {buy_win_rate ? `${buy_win_rate.wins}W / ${buy_win_rate.losses}L · last ${buy_win_rate.n_days}d` : ""}
          </span>
        </div>
        <ProgressBar
          value={buy_win_rate?.win_rate ?? 0}
          color={
            (buy_win_rate?.win_rate ?? 0) >= 60 ? "#16a34a" :
            (buy_win_rate?.win_rate ?? 0) >= 50 ? "#d97706" : "#dc2626"
          }
          label={`${(buy_win_rate?.win_rate ?? 0).toFixed(0)}%`}
        />
      </div>

      {/* Sell accuracy */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-700">Sell Signal Accuracy</h3>
          <ConfidenceBadge n={sell_accuracy?.total ?? 0} />
        </div>
        <div className="flex items-end gap-3 mb-2">
          <span className="text-2xl font-bold text-amber-700">
            {sell_accuracy?.accuracy != null ? `${sell_accuracy.accuracy.toFixed(1)}%` : "—"}
          </span>
          <span className="text-xs text-gray-400 mb-1">
            {sell_accuracy ? `${sell_accuracy.accurate} accurate · last ${sell_accuracy.n_days}d` : ""}
          </span>
        </div>
        <ProgressBar
          value={sell_accuracy?.accuracy ?? 0}
          color={
            (sell_accuracy?.accuracy ?? 0) >= 60 ? "#16a34a" :
            (sell_accuracy?.accuracy ?? 0) >= 50 ? "#d97706" : "#dc2626"
          }
          label={`${(sell_accuracy?.accuracy ?? 0).toFixed(0)}%`}
        />
      </div>

      {/* Avg holding return */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Avg Holding Return</h3>
        <MetricRow
          label="Mean return (30d)"
          value={fmtPct(average_holding_return?.avg_return_pct)}
          sub={`median ${fmtPct(average_holding_return?.median_return_pct)} · σ ${fmtNum(average_holding_return?.std_return_pct)}%`}
        />
        <MetricRow
          label="Sample size"
          value={String(average_holding_return?.sample_size ?? "—")}
        />
      </div>

      {/* Signal decay chart */}
      {decayData.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Signal Decay</h3>
          <p className="text-xs text-gray-400 mb-2">Avg return (%) after signal, by horizon</p>
          <ResponsiveContainer width="100%" height={100}>
            <BarChart data={decayData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#9ca3af" }} axisLine={false} tickLine={false} />
              <YAxis hide />
              <Tooltip
                formatter={(v) => { const n = Number(v); return [`${n >= 0 ? "+" : ""}${n.toFixed(2)}%`, "Avg return"]; }}
                labelStyle={{ fontSize: 11 }}
                contentStyle={{ fontSize: 11 }}
              />
              <ReferenceLine y={0} stroke="#e5e7eb" />
              <Bar dataKey="avg_return_pct" radius={[3, 3, 0, 0]}>
                {decayData.map((d) => (
                  <Cell
                    key={d.label}
                    fill={d.avg_return_pct >= 0 ? "#16a34a" : "#dc2626"}
                    fillOpacity={0.8}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Signal distribution */}
      {signalDistribution.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Signal Distribution
            <span className="ml-2 text-xs font-normal text-gray-400">
              ({metrics.total_signals} total)
            </span>
          </h3>
          <div className="space-y-1.5">
            {signalDistribution.map(([action, count]) => (
              <div key={action} className="flex items-center gap-2">
                <span
                  className="text-xs font-semibold px-2 py-0.5 rounded text-white w-20 text-center"
                  style={{ backgroundColor: ACTION_COLORS[action] ?? "#6b7280" }}
                >
                  {action}
                </span>
                <div className="flex-1">
                  <ProgressBar
                    value={count}
                    max={metrics.total_signals}
                    color={ACTION_COLORS[action] ?? "#6b7280"}
                    label={String(count)}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
