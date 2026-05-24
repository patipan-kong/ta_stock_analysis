"use client";

import type { ActivePolicy, DeploymentBias, StrictnessLevel } from "@/lib/api";

// ─── Config tables ────────────────────────────────────────────────────────────

const BIAS_CFG: Record<DeploymentBias, { label: string; bg: string; text: string; bar: string }> = {
  AGGRESSIVE:   { label: "Aggressive",   bg: "bg-green-50  border-green-300",  text: "text-green-800",  bar: "bg-green-500" },
  SELECTIVE:    { label: "Selective",    bg: "bg-blue-50   border-blue-300",   text: "text-blue-800",   bar: "bg-blue-500" },
  DEFENSIVE:    { label: "Defensive",    bg: "bg-amber-50  border-amber-300",  text: "text-amber-800",  bar: "bg-amber-500" },
  PRESERVATION: { label: "Preservation", bg: "bg-red-50    border-red-300",    text: "text-red-800",    bar: "bg-red-500" },
};

const STRICT_CFG: Record<StrictnessLevel, { label: string; color: string }> = {
  RELAXED:   { label: "Relaxed",   color: "text-green-700 bg-green-50 border-green-200" },
  NORMAL:    { label: "Normal",    color: "text-blue-700  bg-blue-50  border-blue-200" },
  STRICT:    { label: "Strict",    color: "text-amber-700 bg-amber-50 border-amber-200" },
  EMERGENCY: { label: "Emergency", color: "text-red-700   bg-red-50   border-red-200" },
};

const FACTOR_COLORS: Record<string, string> = {
  growth:   "bg-green-500",
  value:    "bg-purple-500",
  momentum: "bg-orange-500",
  quality:  "bg-blue-500",
  dividend: "bg-amber-500",
};

const GOV_FLAG_COLOR = (flag: string): string => {
  if (flag.startsWith("POLICY_VIOLATION"))     return "text-red-700 bg-red-50 border-red-200";
  if (flag.startsWith("CONCENTRATION_BREACH")) return "text-orange-700 bg-orange-50 border-orange-200";
  if (flag.startsWith("OVER_AGGRESSION"))      return "text-amber-700 bg-amber-50 border-amber-200";
  if (flag.startsWith("REGIME_MISMATCH"))      return "text-purple-700 bg-purple-50 border-purple-200";
  return "text-gray-700 bg-gray-50 border-gray-200";
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function ScoreBar({
  label,
  value,
  color = "bg-blue-500",
  suffix = "",
}: {
  label: string;
  value: number;
  color?: string;
  suffix?: string;
}) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-0.5">
        <span className="text-gray-500">{label}</span>
        <span className="font-medium text-gray-700">{Math.round(value)}{suffix}</span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(100, value)}%` }} />
      </div>
    </div>
  );
}

function Stat({ label, value, note }: { label: string; value: string | number; note?: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-gray-400">{label}</span>
      <span className="text-sm font-semibold text-gray-800 tabular-nums">{value}</span>
      {note && <span className="text-xs text-gray-400">{note}</span>}
    </div>
  );
}

// ─── Main card ────────────────────────────────────────────────────────────────

export default function ActivePolicyEnvelopeCard({ policy }: { policy: ActivePolicy }) {
  const biasCfg    = BIAS_CFG[policy.deployment_bias]    ?? BIAS_CFG.SELECTIVE;
  const strictCfg  = STRICT_CFG[policy.strictness_level] ?? STRICT_CFG.NORMAL;
  const hc         = policy.hard_constraints;

  const topTilts = Object.entries(policy.soft_factor_tilts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  const hasGovernanceIssues =
    (policy.governance_flags && policy.governance_flags.length > 0) ||
    (policy.violations && policy.violations.length > 0);

  const riskGovScore = policy.risk_governance_score ?? null;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-700">Active Optimization Policy</span>
          {policy.emergency_override && (
            <span className="text-xs font-bold px-2 py-0.5 rounded border bg-red-100 border-red-300 text-red-800 animate-pulse">
              EMERGENCY
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-medium px-2 py-0.5 rounded border ${strictCfg.color}`}>
            {strictCfg.label}
          </span>
          <span className={`text-xs font-bold px-2 py-0.5 rounded border ${biasCfg.bg} ${biasCfg.text}`}>
            {biasCfg.label}
          </span>
        </div>
      </div>

      {/* ── Emergency banner ── */}
      {policy.emergency_override && policy.emergency_reason && (
        <div className="mb-3 p-2.5 rounded bg-red-50 border border-red-200">
          <p className="text-xs font-medium text-red-800">{policy.emergency_reason}</p>
          <p className="text-xs text-red-600 mt-0.5">All new aggressive allocations frozen. Capital preservation mode active.</p>
        </div>
      )}

      {/* ── Hard constraints grid ── */}
      <div className="grid grid-cols-3 gap-3 mb-3 p-2.5 bg-gray-50 rounded-lg">
        <Stat label="Cash Floor" value={`${hc.min_cash_pct.toFixed(0)}%`} note="minimum undeployed" />
        <Stat label="Max Position" value={`${hc.max_single_position_pct.toFixed(0)}%`} note="single stock" />
        <Stat label="Max Sector" value={`${hc.max_sector_pct.toFixed(0)}%`} note="concentration" />
        <Stat label="Turnover Cap" value={`${hc.max_turnover_pct.toFixed(0)}%`} note="per rebalance" />
        <Stat label="New Positions" value={hc.max_new_positions} note="max this run" />
        <Stat
          label="Speculative"
          value={hc.suppress_speculative ? "Suppressed" : "Allowed"}
          note={hc.suppress_speculative ? "low-quality blocked" : ""}
        />
      </div>

      {/* ── Risk budget bar ── */}
      <div className="mb-3">
        <ScoreBar
          label="Risk Budget"
          value={policy.risk_budget}
          color={
            policy.risk_budget > 60 ? "bg-green-500" :
            policy.risk_budget > 35 ? "bg-blue-500" :
            policy.risk_budget > 15 ? "bg-amber-500" : "bg-red-500"
          }
          suffix="/100"
        />
      </div>

      {/* ── Factor tilts ── */}
      <div className="mb-3">
        <p className="text-xs text-gray-500 mb-1.5">Active Factor Tilt</p>
        <div className="space-y-1">
          {topTilts.map(([factor, weight]) => (
            <div key={factor} className="flex items-center gap-2">
              <span className="text-xs w-16 text-gray-600 capitalize">{factor}</span>
              <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${FACTOR_COLORS[factor] ?? "bg-gray-400"}`}
                  style={{ width: `${Math.min(100, weight * 100)}%` }}
                />
              </div>
              <span className="text-xs w-8 text-right text-gray-500">{Math.round(weight * 100)}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Governance scores ── */}
      {(policy.policy_alignment_score != null ||
        policy.regime_compliance_score != null ||
        riskGovScore != null) && (
        <div className="mb-3 space-y-1.5">
          <p className="text-xs text-gray-500">Policy Governance Scores</p>
          {policy.policy_alignment_score != null && (
            <ScoreBar
              label="Policy Alignment"
              value={policy.policy_alignment_score}
              color={policy.policy_alignment_score >= 80 ? "bg-green-500" : policy.policy_alignment_score >= 55 ? "bg-blue-500" : "bg-red-500"}
              suffix="/100"
            />
          )}
          {policy.regime_compliance_score != null && (
            <ScoreBar
              label="Regime Compliance"
              value={policy.regime_compliance_score}
              color={policy.regime_compliance_score >= 80 ? "bg-green-500" : policy.regime_compliance_score >= 55 ? "bg-amber-500" : "bg-red-500"}
              suffix="/100"
            />
          )}
          {riskGovScore != null && (
            <ScoreBar
              label="Risk Governance"
              value={riskGovScore}
              color={riskGovScore >= 80 ? "bg-green-500" : riskGovScore >= 55 ? "bg-blue-500" : "bg-red-500"}
              suffix="/100"
            />
          )}
        </div>
      )}

      {/* ── Confidence discount ── */}
      {policy.confidence_discount > 0.05 && (
        <div className="mb-3 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1.5">
          Constraints tightened {Math.round(policy.confidence_discount * 100)}% due to low regime
          confidence or transition instability.
        </div>
      )}

      {/* ── Governance flags ── */}
      {policy.governance_flags && policy.governance_flags.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-medium text-gray-600 mb-1">Governance Flags</p>
          <div className="space-y-1">
            {policy.governance_flags.map((flag, i) => (
              <div key={i} className={`text-xs px-2 py-1 rounded border ${GOV_FLAG_COLOR(flag)}`}>
                {flag}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Portfolio violations ── */}
      {policy.violations && policy.violations.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-medium text-gray-600 mb-1">Portfolio Violations</p>
          <div className="space-y-1">
            {policy.violations.map((v, i) => (
              <div key={i} className="text-xs px-2 py-1 rounded border text-red-700 bg-red-50 border-red-200">
                {v}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Narrative ── */}
      <p className="text-xs text-gray-500 leading-relaxed border-t border-gray-100 pt-2 mt-1">
        {policy.policy_narrative}
      </p>
    </div>
  );
}
