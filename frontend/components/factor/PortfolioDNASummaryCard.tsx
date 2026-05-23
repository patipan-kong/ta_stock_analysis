"use client";

import type { StyleClassification, FactorSectorConcentration, FactorExposureMetadata } from "@/lib/api";

const CONFIDENCE_STYLES: Record<string, string> = {
  high:   "bg-emerald-100 text-emerald-800 border border-emerald-200",
  medium: "bg-amber-100 text-amber-800 border border-amber-200",
  low:    "bg-gray-100 text-gray-600 border border-gray-200",
};

const HHI_STYLES: Record<string, string> = {
  LOW:      "bg-emerald-50 text-emerald-700 border border-emerald-200",
  MEDIUM:   "bg-amber-50 text-amber-700 border border-amber-200",
  HIGH:     "bg-orange-50 text-orange-700 border border-orange-200",
  CRITICAL: "bg-red-50 text-red-700 border border-red-200",
};

const FACTOR_COLORS: Record<string, string> = {
  growth:   "#10b981",
  value:    "#3b82f6",
  dividend: "#f59e0b",
  momentum: "#8b5cf6",
  quality:  "#14b8a6",
};

const FACTOR_LABELS: Record<string, string> = {
  growth:   "Growth",
  value:    "Value",
  dividend: "Dividend",
  momentum: "Momentum",
  quality:  "Quality",
};

function DivScoreGauge({ score }: { score: number | null }) {
  if (score == null) return <span className="text-lg font-bold text-gray-400">—</span>;
  const color = score >= 70 ? "text-emerald-600" : score >= 50 ? "text-blue-600" : score >= 30 ? "text-amber-600" : "text-red-600";
  const ring  = score >= 70 ? "#10b981"         : score >= 50 ? "#3b82f6"       : score >= 30 ? "#f59e0b"       : "#ef4444";

  return (
    <div className="flex items-center gap-2">
      <svg width="36" height="36" viewBox="0 0 36 36" className="rotate-[-90deg]">
        <circle cx="18" cy="18" r="14" fill="none" stroke="#f3f4f6" strokeWidth="3.5" />
        <circle
          cx="18" cy="18" r="14" fill="none"
          stroke={ring} strokeWidth="3.5"
          strokeDasharray={`${(score / 100) * 87.96} 87.96`}
          strokeLinecap="round"
        />
      </svg>
      <span className={`text-xl font-bold tabular-nums ${color}`}>{score.toFixed(0)}</span>
    </div>
  );
}

interface Props {
  portfolioName: string;
  generatedAt: string;
  style: StyleClassification;
  sector: FactorSectorConcentration;
  metadata: FactorExposureMetadata;
}

export default function PortfolioDNASummaryCard({ portfolioName, generatedAt, style, sector, metadata }: Props) {
  const hhiLabel = sector.hhi_label;
  const lowDataFlags = metadata.data_quality_flags.filter(f => f.includes("LOW_DATA_COVERAGE"));
  const partialFlags = metadata.data_quality_flags.filter(f => f.includes("PARTIAL_DATA"));
  const totalFlagCount = lowDataFlags.length + partialFlags.length;
  const genDate = new Date(generatedAt).toLocaleTimeString("en-US", {
    hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Bangkok",
  });

  return (
    <div className="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
      {/* Accent stripe */}
      <div className="h-1 w-full bg-gradient-to-r from-blue-500 via-purple-500 to-teal-500" />

      <div className="p-6">
        {/* Top row: title + badges */}
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-5">
          <div>
            <p className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-1.5">
              Portfolio DNA — {portfolioName}
            </p>
            <h2 className="text-3xl font-black text-gray-900 leading-tight">{style.primary}</h2>
            {style.secondary && (
              <p className="text-sm text-gray-500 mt-1">
                with <span className="font-medium text-gray-700">{style.secondary}</span> characteristics
              </p>
            )}
          </div>
          <div className="flex flex-row sm:flex-col items-start sm:items-end gap-2 shrink-0">
            <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full whitespace-nowrap ${CONFIDENCE_STYLES[style.confidence] ?? ""}`}>
              {style.confidence.toUpperCase()} CONFIDENCE
            </span>
            {hhiLabel && (
              <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full whitespace-nowrap ${HHI_STYLES[hhiLabel] ?? ""}`}>
                {hhiLabel} CONCENTRATION
              </span>
            )}
          </div>
        </div>

        {/* Dominant factor chips */}
        {style.dominant_factors.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            <span className="text-xs text-gray-400 self-center mr-1">Driven by:</span>
            {style.dominant_factors.map(f => {
              const col = FACTOR_COLORS[f] ?? "#6b7280";
              return (
                <span
                  key={f}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full"
                  style={{
                    backgroundColor: `${col}15`,
                    color: col,
                    border: `1px solid ${col}35`,
                  }}
                >
                  <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: col }} />
                  {FACTOR_LABELS[f] ?? f}
                </span>
              );
            })}
          </div>
        )}

        {/* Rationale */}
        <blockquote className="text-sm text-gray-600 leading-relaxed border-l-[3px] border-blue-400 pl-4 py-1 mb-5 italic bg-blue-50/40 rounded-r-lg pr-3">
          {style.rationale}
        </blockquote>

        {/* Stats strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-gray-100">
          <div>
            <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wide mb-1">Diversification</p>
            <DivScoreGauge score={sector.diversification_score} />
            <p className="text-[11px] text-gray-400 mt-0.5">out of 100</p>
          </div>
          <div>
            <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wide mb-1">Universe</p>
            <p className="text-xl font-bold text-gray-900">{metadata.universe_size}</p>
            <p className="text-[11px] text-gray-400">holdings analyzed</p>
          </div>
          <div>
            <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wide mb-1">Data Quality</p>
            <p className={`text-xl font-bold ${totalFlagCount === 0 ? "text-emerald-600" : totalFlagCount <= 2 ? "text-amber-600" : "text-red-600"}`}>
              {totalFlagCount === 0 ? "Full" : `${totalFlagCount} gap${totalFlagCount > 1 ? "s" : ""}`}
            </p>
            <p className="text-[11px] text-gray-400">coverage status</p>
          </div>
          <div>
            <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wide mb-1">Computed</p>
            <p className="text-xl font-bold text-gray-900">{genDate}</p>
            <p className="text-[11px] text-gray-400">ICT · 15 min cache</p>
          </div>
        </div>

        {/* Coverage warnings */}
        {metadata.data_quality_flags.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {metadata.data_quality_flags.map(flag => {
              const [sym, kind] = flag.split(":");
              const isLow = kind === "LOW_DATA_COVERAGE";
              return (
                <span
                  key={flag}
                  className={`text-[11px] font-medium px-2 py-0.5 rounded border ${
                    isLow
                      ? "bg-red-50 text-red-700 border-red-200"
                      : "bg-amber-50 text-amber-700 border-amber-200"
                  }`}
                >
                  {sym} · {isLow ? "Low data" : "Partial data"}
                </span>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
