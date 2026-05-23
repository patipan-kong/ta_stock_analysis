"use client";

import type { FactorExposureResult, StyleClassification, FactorSectorConcentration } from "@/lib/api";

const STYLE_ICONS: Record<string, string> = {
  "Quality Growth":          "◆",
  "Momentum Growth":         "▲",
  "GARP":                    "⬟",
  "Value Income":            "💠",
  "Conservative Quality":    "◈",
  "Quality Income":          "⬡",
  "Momentum Quality":        "▶",
  "Dividend Growth":         "⊕",
  "Tactical Value":          "◇",
  "Tactical Income":         "⊞",
  "Growth Tilt":             "↑",
  "Value Defensive":         "⊟",
  "Dividend Income":         "⊕",
  "Momentum Aggressive":     "⚡",
  "Quality Core":            "◆",
  "Balanced Core":           "⊜",
  "Defensive Conservative":  "⊘",
};

function buildInsights(
  style: StyleClassification,
  sector: FactorSectorConcentration,
  exposures: FactorExposureResult["factor_exposures"],
): string[] {
  const insights: string[] = [];

  // Primary style insight
  const styleName = style.primary;
  const topFactors = style.dominant_factors;
  if (topFactors.length >= 2) {
    const [f1, f2] = topFactors;
    const s1 = exposures[f1 as keyof typeof exposures]?.score;
    const s2 = exposures[f2 as keyof typeof exposures]?.score;
    if (s1 != null && s2 != null) {
      insights.push(
        `Portfolio currently behaves like a ${styleName} strategy — combining strong ${f1} (${s1.toFixed(0)}/100) with ${f2} (${s2.toFixed(0)}/100) characteristics.`
      );
    } else {
      insights.push(`Portfolio exhibits a ${styleName} investment profile based on current holdings.`);
    }
  } else if (topFactors.length === 1) {
    const f = topFactors[0];
    const s = exposures[f as keyof typeof exposures]?.score;
    insights.push(
      s != null
        ? `Portfolio is predominantly ${f}-driven (${s.toFixed(0)}/100), consistent with a ${styleName} orientation.`
        : `Portfolio has a strong ${styleName} tilt with ${f} as the primary driver.`
    );
  } else {
    insights.push(`Portfolio style classified as "${styleName}" — ${style.rationale.split(".")[0]}.`);
  }

  // Sector concentration insight
  const { top_sector, top_sector_weight, diversification_score, concentration_flags } = sector;
  if (concentration_flags.includes("SINGLE_SECTOR") && top_sector) {
    insights.push(`All holdings concentrated in ${top_sector} — consider adding cross-sector exposure to reduce idiosyncratic risk.`);
  } else if (top_sector && top_sector_weight != null && top_sector_weight > 50) {
    insights.push(`${top_sector} sector dominates at ${top_sector_weight.toFixed(0)}% — significant single-sector exposure above healthy diversification thresholds.`);
  } else if (top_sector && top_sector_weight != null && top_sector_weight > 35) {
    insights.push(`${top_sector} sector concentration at ${top_sector_weight.toFixed(0)}% exceeds the 35% healthy diversification threshold.`);
  } else if (diversification_score != null && diversification_score >= 70) {
    insights.push(`Sector allocation is well-diversified (score ${diversification_score.toFixed(0)}/100) — no single sector dominates.`);
  }

  // Quality insight
  const qualityScore = exposures.quality?.score;
  const growthScore  = exposures.growth?.score;
  const momentumScore = exposures.momentum?.score;
  const valueScore   = exposures.value?.score;
  const divScore     = exposures.dividend?.score;

  if (qualityScore != null && qualityScore >= 70 && growthScore != null && growthScore >= 60) {
    insights.push(`High quality-growth combination suggests portfolio holds compounders — businesses with durable competitive advantages and expanding earnings.`);
  } else if (valueScore != null && valueScore >= 70 && divScore != null && divScore >= 60) {
    insights.push(`Strong value-dividend combination indicates portfolio is positioned for income generation at attractive valuations.`);
  } else if (momentumScore != null && momentumScore <= 30) {
    insights.push(`Momentum exposure is weak (${momentumScore.toFixed(0)}/100) — several holdings may be in downtrends or consolidation phases.`);
  } else if (momentumScore != null && momentumScore >= 75) {
    insights.push(`Strong price momentum (${momentumScore.toFixed(0)}/100) across holdings — portfolio is in favorable technical territory.`);
  }

  return insights.slice(0, 3);
}

const INSIGHT_COLORS = [
  { accent: "#3b82f6", bg: "bg-blue-50/60",   border: "border-blue-200" },
  { accent: "#f59e0b", bg: "bg-amber-50/60",  border: "border-amber-200" },
  { accent: "#8b5cf6", bg: "bg-purple-50/60", border: "border-purple-200" },
];

interface Props {
  style: StyleClassification;
  sector: FactorSectorConcentration;
  factorExposures: FactorExposureResult["factor_exposures"];
  rawMetrics: FactorExposureResult["raw_metrics_summary"];
}

export default function PortfolioDriftInsight({ style, sector, factorExposures, rawMetrics }: Props) {
  const icon = STYLE_ICONS[style.primary] ?? "◈";
  const insights = buildInsights(style, sector, factorExposures);

  const avgPE    = rawMetrics.avg_pe;
  const avgROE   = rawMetrics.avg_roe;
  const avgDiv   = rawMetrics.avg_dividend_yield;
  const avgRev   = rawMetrics.avg_revenue_growth;
  const avgRet30 = rawMetrics.avg_return_30d;

  return (
    <div className="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
      {/* Header gradient strip */}
      <div
        className="px-5 pt-5 pb-4"
        style={{
          background: "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
        }}
      >
        <div className="flex items-center gap-3 mb-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center text-xl"
            style={{ background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.15)" }}
          >
            {icon}
          </div>
          <div>
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Portfolio Drift Insight</p>
            <h3 className="text-base font-black text-white">{style.primary}</h3>
          </div>
        </div>
      </div>

      {/* Insight bullets */}
      <div className="px-5 pt-4 pb-2 space-y-3">
        {insights.map((text, i) => {
          const cfg = INSIGHT_COLORS[i % INSIGHT_COLORS.length];
          return (
            <div
              key={i}
              className={`flex gap-3 p-3 rounded-xl border ${cfg.bg} ${cfg.border}`}
            >
              <span
                className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0"
                style={{ backgroundColor: cfg.accent }}
              />
              <p className="text-sm text-gray-700 leading-relaxed">{text}</p>
            </div>
          );
        })}
      </div>

      {/* Raw metrics strip */}
      <div className="px-5 pb-5 pt-3">
        <p className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-3">Portfolio Averages</p>
        <div className="grid grid-cols-3 sm:grid-cols-5 gap-3">
          {[
            { label: "Avg P/E",     value: avgPE    != null ? avgPE.toFixed(1)           : "—", sub: "valuation" },
            { label: "Avg ROE",     value: avgROE   != null ? `${(avgROE * 100).toFixed(1)}%`   : "—", sub: "quality" },
            { label: "Div Yield",   value: avgDiv   != null ? `${(avgDiv * 100).toFixed(2)}%`   : "—", sub: "income" },
            { label: "Rev Growth",  value: avgRev   != null ? `${(avgRev * 100).toFixed(1)}%`   : "—", sub: "growth" },
            { label: "30d Return",  value: avgRet30 != null ? `${(avgRet30 * 100).toFixed(1)}%` : "—",
              sub: "momentum",
              highlight: avgRet30 != null ? (avgRet30 > 0 ? "pos" : "neg") : null },
          ].map(({ label, value, sub, highlight }) => (
            <div key={label} className="bg-gray-50 rounded-xl p-2.5 text-center">
              <p className="text-[10px] text-gray-400 mb-0.5 font-medium">{label}</p>
              <p className={`text-sm font-bold tabular-nums ${
                highlight === "pos" ? "text-emerald-600" :
                highlight === "neg" ? "text-red-600" :
                "text-gray-900"
              }`}>
                {value}
              </p>
              <p className="text-[10px] text-gray-400">{sub}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
