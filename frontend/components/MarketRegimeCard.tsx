"use client";

import type { MarketRegime } from "@/lib/api";

// ─── Regime config ────────────────────────────────────────────────────────────

type RegimeKey =
  | "RISK_ON"
  | "RISK_OFF"
  | "SIDEWAYS"
  | "HIGH_VOLATILITY"
  | "DEFENSIVE_REGIME"
  | "TRANSITION_RISK_ON"
  | "TRANSITION_RISK_OFF";

const REGIME_CFG: Record<
  RegimeKey,
  { label: string; icon: string; bg: string; border: string; text: string; bar: string; dot: string }
> = {
  RISK_ON: {
    label: "Risk On",
    icon: "▲",
    bg: "bg-emerald-50",
    border: "border-emerald-300",
    text: "text-emerald-800",
    bar: "bg-emerald-500",
    dot: "bg-emerald-500",
  },
  RISK_OFF: {
    label: "Risk Off",
    icon: "▼",
    bg: "bg-red-50",
    border: "border-red-300",
    text: "text-red-800",
    bar: "bg-red-500",
    dot: "bg-red-500",
  },
  SIDEWAYS: {
    label: "Sideways",
    icon: "→",
    bg: "bg-gray-50",
    border: "border-gray-300",
    text: "text-gray-700",
    bar: "bg-gray-400",
    dot: "bg-gray-400",
  },
  HIGH_VOLATILITY: {
    label: "High Volatility",
    icon: "⚡",
    bg: "bg-orange-50",
    border: "border-orange-300",
    text: "text-orange-800",
    bar: "bg-orange-500",
    dot: "bg-orange-500",
  },
  DEFENSIVE_REGIME: {
    label: "Defensive",
    icon: "◉",
    bg: "bg-blue-50",
    border: "border-blue-300",
    text: "text-blue-800",
    bar: "bg-blue-500",
    dot: "bg-blue-500",
  },
  TRANSITION_RISK_ON: {
    label: "Transitioning ↑",
    icon: "◈",
    bg: "bg-teal-50",
    border: "border-teal-300",
    text: "text-teal-800",
    bar: "bg-teal-500",
    dot: "bg-teal-500",
  },
  TRANSITION_RISK_OFF: {
    label: "Transitioning ↓",
    icon: "◈",
    bg: "bg-amber-50",
    border: "border-amber-300",
    text: "text-amber-800",
    bar: "bg-amber-500",
    dot: "bg-amber-500",
  },
};

const STABILITY_CFG = {
  STABLE:        { label: "Stable",        color: "text-emerald-600", dot: "bg-emerald-500" },
  TRANSITIONING: { label: "Transitioning", color: "text-amber-600",   dot: "bg-amber-500"   },
  VOLATILE:      { label: "Volatile",      color: "text-red-600",     dot: "bg-red-500"      },
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function ScoreBar({
  label,
  value,
  barColor,
}: {
  label: string;
  value: number;
  barColor: string;
}) {
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs text-gray-500">{label}</span>
        <span className="text-xs font-mono font-semibold text-gray-700">{Math.round(value)}</span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
    </div>
  );
}

function ConfidenceMeter({ pct, barColor }: { pct: number; barColor: string }) {
  const segments = [0, 20, 40, 60, 80];
  return (
    <div className="flex gap-0.5 items-end h-5">
      {segments.map((threshold, i) => (
        <div
          key={i}
          className={`rounded-sm transition-all duration-500 ${
            pct >= threshold + 20
              ? barColor
              : "bg-gray-100"
          }`}
          style={{ width: 10, height: 8 + i * 3 }}
        />
      ))}
    </div>
  );
}

// ─── Historical timeline dots ─────────────────────────────────────────────────

function RegimeTimeline({ history }: { history: { date: string; regime: string; confidence: number }[] }) {
  const recent = history.slice(-14);
  return (
    <div className="flex gap-1 items-center flex-wrap">
      {recent.map((h, i) => {
        const cfg = REGIME_CFG[h.regime as RegimeKey];
        return (
          <div
            key={i}
            title={`${h.date}: ${h.regime} (${h.confidence}%)`}
            className={`w-3 h-3 rounded-full ${cfg?.dot ?? "bg-gray-300"} opacity-${
              50 + Math.round((i / recent.length) * 50)
            }`}
            style={{ opacity: 0.3 + (i / Math.max(recent.length - 1, 1)) * 0.7 }}
          />
        );
      })}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

interface Props {
  regime: MarketRegime;
  compact?: boolean;
}

export default function MarketRegimeCard({ regime, compact = false }: Props) {
  const key = regime.regime as RegimeKey;
  const cfg = REGIME_CFG[key] ?? REGIME_CFG.SIDEWAYS;
  const stability = STABILITY_CFG[regime.transition_stability as keyof typeof STABILITY_CFG] ?? STABILITY_CFG.STABLE;

  if (compact) {
    return (
      <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border ${cfg.bg} ${cfg.border}`}>
        <span className={`text-base font-bold ${cfg.text}`}>{cfg.icon}</span>
        <span className={`text-sm font-bold ${cfg.text}`}>{cfg.label}</span>
        <span className="text-xs text-gray-500">{regime.confidence_pct?.toFixed(0)}%</span>
      </div>
    );
  }

  return (
    <div className={`rounded-2xl border-2 ${cfg.border} ${cfg.bg} p-5 space-y-4 shadow-sm`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center text-xl font-bold ${cfg.text} bg-white/70`}
          >
            {cfg.icon}
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">Market Regime</p>
            <h3 className={`text-xl font-bold ${cfg.text}`}>{cfg.label}</h3>
          </div>
        </div>

        {/* Confidence meter */}
        <div className="flex flex-col items-end gap-1">
          <ConfidenceMeter pct={regime.confidence_pct ?? 0} barColor={cfg.bar} />
          <span className="text-xs text-gray-500 font-mono">{regime.confidence_pct?.toFixed(0)}% confidence</span>
        </div>
      </div>

      {/* Narrative */}
      {regime.narrative && (
        <p className={`text-sm leading-relaxed ${cfg.text} bg-white/50 rounded-xl px-4 py-2.5 border ${cfg.border}`}>
          {regime.narrative}
        </p>
      )}

      {/* Signal bars */}
      <div className="grid grid-cols-2 gap-3 bg-white/60 rounded-xl p-3">
        <ScoreBar label="Trend"       value={regime.trend_score ?? 50}      barColor={cfg.bar} />
        <ScoreBar label="Calm (vs vol)" value={regime.volatility_score ?? 50} barColor={cfg.bar} />
        <ScoreBar label="Drawdown"    value={regime.drawdown_score ?? 50}   barColor={cfg.bar} />
        <ScoreBar label="Momentum"    value={regime.momentum_score ?? 50}   barColor={cfg.bar} />
      </div>

      {/* Meta row */}
      <div className="flex flex-wrap gap-x-4 gap-y-2 text-xs text-gray-600">
        <span>
          <span className="text-gray-400">Duration</span>{" "}
          <strong className="text-gray-700">{regime.regime_duration_days ?? 1}d</strong>
        </span>
        <span>
          <span className="text-gray-400">Prev</span>{" "}
          <strong className="text-gray-700">{regime.previous_regime ?? "—"}</strong>
        </span>
        <span className="flex items-center gap-1">
          <span className={`w-2 h-2 rounded-full ${stability.dot}`} />
          <span className={stability.color}>{stability.label}</span>
        </span>
        {regime.vix_level != null && (
          <span>
            <span className="text-gray-400">VIX</span>{" "}
            <strong className={regime.vix_level > 25 ? "text-orange-600" : "text-gray-700"}>
              {regime.vix_level.toFixed(1)}
            </strong>
          </span>
        )}
      </div>

      {/* History dots */}
      {regime.regime_history && regime.regime_history.length > 1 && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400 shrink-0">30d history</span>
          <RegimeTimeline history={regime.regime_history} />
        </div>
      )}

      {/* Transition warnings */}
      {regime.transition_warnings && regime.transition_warnings.length > 0 && (
        <div className="space-y-1">
          {regime.transition_warnings.map((w, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              <span className="shrink-0 mt-0.5">⚠</span>
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
