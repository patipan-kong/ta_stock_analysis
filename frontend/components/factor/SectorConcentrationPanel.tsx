"use client";

import { sectorColor } from "@/lib/sectors";
import type { FactorSectorConcentration } from "@/lib/api";

const HHI_CONFIG: Record<string, { label: string; color: string; bg: string; border: string; desc: string }> = {
  LOW:      { label: "Low",      color: "#059669", bg: "#f0fdf4", border: "#a7f3d0", desc: "Well diversified across sectors" },
  MEDIUM:   { label: "Medium",   color: "#d97706", bg: "#fffbeb", border: "#fde68a", desc: "Moderate sector concentration" },
  HIGH:     { label: "High",     color: "#ea580c", bg: "#fff7ed", border: "#fed7aa", desc: "Elevated concentration risk" },
  CRITICAL: { label: "Critical", color: "#dc2626", bg: "#fef2f2", border: "#fecaca", desc: "Heavy concentration in few sectors" },
};

const FLAG_DISPLAY: Record<string, { label: string; sev: "warn" | "err" }> = {
  "SECTOR_OVER_35_PCT": { label: "A sector exceeds 35% allocation",   sev: "warn" },
  "SINGLE_SECTOR":      { label: "All holdings in one sector",         sev: "err"  },
  "ONLY_TWO_SECTORS":   { label: "Only two sectors represented",       sev: "warn" },
};

function DivScoreBar({ score }: { score: number | null }) {
  if (score == null) return null;
  const color = score >= 70 ? "#10b981" : score >= 50 ? "#3b82f6" : score >= 30 ? "#f59e0b" : "#ef4444";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-100 rounded-full h-1.5 overflow-hidden">
        <div className="h-1.5 rounded-full" style={{ width: `${score}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs font-bold tabular-nums w-8 text-right" style={{ color }}>
        {score.toFixed(0)}
      </span>
    </div>
  );
}

interface Props {
  sector: FactorSectorConcentration;
}

export default function SectorConcentrationPanel({ sector }: Props) {
  // Backend returns sector_concentration: {} for empty portfolios, and may emit
  // null weights — default every field and coerce before sorting/formatting.
  const {
    sector_weights = {},
    top_sector = null,
    top_sector_weight = null,
    diversification_score = null,
    hhi = null,
    hhi_label = null,
    concentration_flags = [],
  } = sector ?? {};
  const hhiCfg = hhi_label ? (HHI_CONFIG[hhi_label] ?? HHI_CONFIG.MEDIUM) : null;
  const entries = Object.entries(sector_weights)
    .map(([sec, w]) => [sec, w ?? 0] as [string, number])
    .sort(([, a], [, b]) => b - a);

  const dominantFlag = concentration_flags.find(f => f.startsWith("DOMINANT_SECTOR:"));
  const dominantSector = dominantFlag
    ? dominantFlag.replace("DOMINANT_SECTOR:", "").replace(/_/g, " ")
    : null;

  return (
    <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-5">
      {/* Header */}
      <div className="flex items-start justify-between mb-5">
        <div>
          <h3 className="text-sm font-bold text-gray-800">Sector Concentration</h3>
          <p className="text-xs text-gray-400 mt-0.5">Portfolio weight distribution across sectors</p>
        </div>
        {hhiCfg && (
          <div
            className="text-right px-3 py-2 rounded-xl border"
            style={{ backgroundColor: hhiCfg.bg, borderColor: hhiCfg.border }}
          >
            <p className="text-[11px] font-bold uppercase tracking-wide" style={{ color: hhiCfg.color }}>
              HHI: {hhi_label}
            </p>
            <p className="text-[11px] text-gray-500 mt-0.5">{hhiCfg.desc}</p>
            {hhi != null && (
              <p className="text-[11px] font-semibold tabular-nums mt-0.5" style={{ color: hhiCfg.color }}>
                {hhi.toFixed(0)} / 10,000
              </p>
            )}
          </div>
        )}
      </div>

      {/* Concentration flags */}
      {concentration_flags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {concentration_flags
            .filter(f => !f.startsWith("DOMINANT_SECTOR:"))
            .map(flag => {
              const cfg = FLAG_DISPLAY[flag];
              if (!cfg) return null;
              return (
                <div
                  key={flag}
                  className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-lg border ${
                    cfg.sev === "err"
                      ? "bg-red-50 text-red-700 border-red-200"
                      : "bg-amber-50 text-amber-700 border-amber-200"
                  }`}
                >
                  <span>{cfg.sev === "err" ? "⚠" : "!"}</span>
                  {cfg.label}
                </div>
              );
            })}
          {dominantSector && (
            <div className="flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-lg border bg-orange-50 text-orange-700 border-orange-200">
              <span>⬆</span>
              {dominantSector} dominates portfolio (&gt;50%)
            </div>
          )}
        </div>
      )}

      {/* Sector bars */}
      <div className="space-y-3">
        {entries.map(([sec, weight]) => {
          const isTop = sec === top_sector;
          const col   = sectorColor(sec);
          return (
            <div key={sec}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span
                    className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
                    style={{ backgroundColor: col }}
                  />
                  <span className={`text-xs font-medium ${isTop ? "text-gray-900" : "text-gray-700"}`}>
                    {sec}
                  </span>
                  {isTop && top_sector_weight != null && top_sector_weight > 35 && (
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 border border-orange-200">
                      OVERWEIGHT
                    </span>
                  )}
                </div>
                <span className={`text-xs font-bold tabular-nums ${isTop ? "text-gray-900" : "text-gray-600"}`}>
                  {weight.toFixed(1)}%
                </span>
              </div>
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-2 rounded-full transition-all duration-700"
                  style={{ width: `${weight}%`, backgroundColor: col, opacity: isTop ? 1 : 0.75 }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Diversification score */}
      {diversification_score != null && (
        <div className="mt-5 pt-4 border-t border-gray-50">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium text-gray-500">Diversification Score</span>
            <span className="text-xs text-gray-400">
              {diversification_score >= 70 ? "Well diversified" : diversification_score >= 50 ? "Moderate" : "Concentrated"}
            </span>
          </div>
          <DivScoreBar score={diversification_score} />
        </div>
      )}
    </div>
  );
}
