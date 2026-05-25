"use client";

import type {
  ActivePolicy,
  ConstraintBreakdown,
  ConstraintSource,
  ConstraintTier,
  DeploymentBias,
  EffectiveEnvelope,
  PolicyViolationDetail,
  StrictnessLevel,
} from "@/lib/api";

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
  // Authorized turnover expansions display as informational, not as failures
  if (flag.startsWith("POLICY_VIOLATION") && flag.toLowerCase().includes("turnover"))
    return "text-blue-700 bg-blue-50 border-blue-200";
  if (flag.startsWith("POLICY_VIOLATION"))     return "text-red-700 bg-red-50 border-red-200";
  if (flag.startsWith("CONCENTRATION_BREACH")) return "text-orange-700 bg-orange-50 border-orange-200";
  if (flag.startsWith("OVER_AGGRESSION"))      return "text-amber-700 bg-amber-50 border-amber-200";
  if (flag.startsWith("REGIME_MISMATCH"))      return "text-purple-700 bg-purple-50 border-purple-200";
  return "text-gray-700 bg-gray-50 border-gray-200";
};

// ─── Constraint comparison helpers ────────────────────────────────────────────

const SOURCE_BADGE: Record<ConstraintSource, { label: string; color: string }> = {
  USER_PREFERENCE:    { label: "User",      color: "text-gray-600  bg-gray-50   border-gray-200" },
  REGIME_POLICY:      { label: "Regime",    color: "text-blue-700  bg-blue-50   border-blue-200" },
  EMERGENCY_OVERRIDE: { label: "Emergency", color: "text-red-700   bg-red-50    border-red-200" },
  SYSTEM_SAFETY:      { label: "System",    color: "text-purple-700 bg-purple-50 border-purple-200" },
};

const VIOLATION_COLOR: Record<string, string> = {
  SECTOR_LIMIT:          "text-amber-700 bg-amber-50 border-amber-200",
  SINGLE_POSITION_LIMIT: "text-orange-700 bg-orange-50 border-orange-200",
  CASH_BREACH:           "text-red-700   bg-red-50   border-red-200",
  TURNOVER_BREACH:       "text-teal-700  bg-teal-50  border-teal-200",
  BETA_EXPOSURE:         "text-purple-700 bg-purple-50 border-purple-200",
  TURNOVER_RELAXED:      "text-teal-600  bg-teal-50  border-teal-200",
};

const VIOLATION_FRIENDLY_NAME: Record<string, string> = {
  SECTOR_LIMIT:          "Sector Limit",
  SINGLE_POSITION_LIMIT: "Position Concentration",
  CASH_BREACH:           "Cash Mandate Breach",
  TURNOVER_BREACH:       "Temporary Turnover Expansion Authorized",
  BETA_EXPOSURE:         "Risk Exposure",
  TURNOVER_RELAXED:      "Authorized Relaxation",
};

const TIER_LABEL: Record<ConstraintTier, { label: string; color: string }> = {
  TIER1_CRITICAL:   { label: "Tier 1 — Critical",  color: "text-red-700    bg-red-50    border-red-200" },
  TIER2_STRATEGIC:  { label: "Tier 2 — Strategic", color: "text-amber-700  bg-amber-50  border-amber-200" },
  TIER3_EFFICIENCY: { label: "Tier 3 — Efficiency", color: "text-blue-600  bg-blue-50   border-blue-200" },
};

function TurnoverRelaxationNotice({
  relaxedCap,
  baseCap,
  reason,
}: {
  relaxedCap: number;
  baseCap: number;
  reason?: string | null;
}) {
  const pctIncrease = Math.round(((relaxedCap / baseCap) - 1) * 100);
  return (
    <div className="mb-3 p-2.5 rounded-lg bg-blue-50 border border-blue-200">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-xs font-semibold text-blue-800">Temporary Turnover Expansion Authorized</span>
        <span className="text-xs px-1.5 py-0.5 rounded border bg-blue-100 border-blue-300 text-blue-700 font-medium tabular-nums">
          +{pctIncrease}%
        </span>
        <span className="text-xs text-blue-600 ml-auto tabular-nums">
          {baseCap.toFixed(0)}% → {relaxedCap.toFixed(0)}%
        </span>
      </div>
      <p className="text-xs text-blue-700 leading-relaxed">
        The system intentionally authorized a temporary turnover ceiling expansion
        ({baseCap.toFixed(0)}% → {relaxedCap.toFixed(0)}%) to eliminate a more dangerous
        Tier 1 concentration risk. This is a controlled optimization adjustment, not a failure.
      </p>
      {reason && (
        <p className="text-xs text-blue-600 mt-0.5 leading-relaxed italic">
          Concentration remediation target: {reason}
        </p>
      )}
      <p className="text-xs text-blue-500 mt-1">
        Tier 1 concentration safety takes precedence over Tier 3 turnover efficiency
      </p>
    </div>
  );
}

function SourceBadge({ source }: { source: ConstraintSource }) {
  const cfg = SOURCE_BADGE[source] ?? SOURCE_BADGE.USER_PREFERENCE;
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded border font-medium ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

function ConstraintRow({
  label,
  bd,
  unit = "%",
  lowerIsTighter = true,
}: {
  label: string;
  bd: ConstraintBreakdown;
  unit?: string;
  lowerIsTighter?: boolean;
}) {
  const isTightened = bd.tightened_reason !== null;
  const effectiveCls = isTightened ? "text-amber-700 font-bold" : "text-gray-800 font-medium";

  return (
    <tr className="border-b border-gray-100 last:border-0">
      <td className="py-1.5 pr-2 text-xs text-gray-500 whitespace-nowrap">{label}</td>
      <td className="py-1.5 px-2 text-xs text-center text-gray-700">
        {bd.user_pref.toFixed(0)}{unit}
      </td>
      <td className="py-1.5 px-2 text-xs text-center text-blue-700">
        {bd.regime_policy.toFixed(0)}{unit}
      </td>
      <td className="py-1.5 px-2 text-xs text-center">
        <span className={effectiveCls}>{bd.effective.toFixed(0)}{unit}</span>
      </td>
      <td className="py-1.5 pl-2 text-xs">
        {isTightened && <SourceBadge source={bd.binding_source} />}
      </td>
    </tr>
  );
}

function ConstraintComparisonTable({ envelope }: { envelope: EffectiveEnvelope }) {
  const sectorEntries = Object.entries(envelope.sector_limits).filter(
    ([s]) => s !== "Other"
  );
  const hasSectorAdjustments = sectorEntries.some(
    ([, bd]) => bd.tightened_reason !== null
  );

  return (
    <div className="mb-3">
      <p className="text-xs font-medium text-gray-600 mb-1.5">Constraint Resolution</p>
      <div className="rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="py-1.5 pr-2 text-left text-xs font-medium text-gray-500">Constraint</th>
              <th className="py-1.5 px-2 text-center text-xs font-medium text-gray-500">User Pref</th>
              <th className="py-1.5 px-2 text-center text-xs font-medium text-blue-600">Active Policy</th>
              <th className="py-1.5 px-2 text-center text-xs font-medium text-gray-800">Effective</th>
              <th className="py-1.5 pl-2 text-left text-xs font-medium text-gray-400">Source</th>
            </tr>
          </thead>
          <tbody className="bg-white">
            <ConstraintRow label="Max Position" bd={envelope.single_position} />
            <ConstraintRow label="Cash Floor" bd={envelope.cash_min} lowerIsTighter={false} />
            <ConstraintRow label="Turnover Cap" bd={envelope.turnover_max} />
            {sectorEntries.map(([sector, bd]) => (
              <ConstraintRow key={sector} label={`${sector} sector`} bd={bd} />
            ))}
          </tbody>
        </table>
      </div>
      {envelope.resolver_notes.length > 0 && (
        <div className="mt-1.5 space-y-0.5">
          {envelope.resolver_notes.slice(0, 4).map((note, i) => (
            <p key={i} className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded px-2 py-1">
              {note}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

function PolicyViolationList({ violations }: { violations: PolicyViolationDetail[] }) {
  if (!violations || violations.length === 0) return null;
  const realViolations = violations.filter(v => v.violation_type !== "TURNOVER_RELAXED");
  if (realViolations.length === 0) return null;

  // Sort by tier severity: Tier 1 first
  const TIER_ORDER: Record<string, number> = { TIER1_CRITICAL: 0, TIER2_STRATEGIC: 1, TIER3_EFFICIENCY: 2 };
  const sorted = [...realViolations].sort(
    (a, b) => (TIER_ORDER[a.tier ?? "TIER3_EFFICIENCY"] ?? 2) - (TIER_ORDER[b.tier ?? "TIER3_EFFICIENCY"] ?? 2)
  );

  // If only authorized operational adjustments remain, use softer header
  const _AUTHORIZED_TYPES = new Set(["TURNOVER_BREACH", "TURNOVER_RELAXED"]);
  const hasOnlyAuthorized = sorted.every(v => _AUTHORIZED_TYPES.has(v.violation_type));
  const headerText = hasOnlyAuthorized ? "Controlled Optimization Adjustment" : "Policy Violations Detected";

  return (
    <div className="mb-3">
      <p className="text-xs font-medium text-gray-600 mb-1">{headerText}</p>
      <div className="space-y-1">
        {sorted.map((v, i) => {
          const cls      = VIOLATION_COLOR[v.violation_type] ?? "text-gray-700 bg-gray-50 border-gray-200";
          const label    = v.sector ?? v.symbol ?? v.violation_type;
          const tierCfg  = v.tier ? TIER_LABEL[v.tier as ConstraintTier] : null;
          const friendlyName = VIOLATION_FRIENDLY_NAME[v.violation_type] ?? v.violation_type.replace(/_/g, " ");
          return (
            <div key={i} className={`text-xs px-2 py-1.5 rounded border ${cls}`}>
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="font-medium">{friendlyName}</span>
                {label && label !== v.violation_type && (
                  <span className="opacity-75">— {label}</span>
                )}
                <span className="opacity-75">
                  ({v.proposed_pct.toFixed(1)}% / {v.allowed_pct.toFixed(0)}% limit)
                </span>
                <SourceBadge source={v.violation_source} />
                {tierCfg && (
                  <span className={`text-xs px-1 py-0.5 rounded border font-medium ${tierCfg.color}`}>
                    {tierCfg.label}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

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

export default function ActivePolicyEnvelopeCard({
  policy,
  effectiveEnvelope,
}: {
  policy: ActivePolicy;
  effectiveEnvelope?: EffectiveEnvelope | null;
}) {
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

      {/* ── Phase 3B.6 — Turnover relaxation notice ── */}
      {policy.turnover_relaxation_active && policy.relaxed_turnover_cap != null && (
        <TurnoverRelaxationNotice
          relaxedCap={policy.relaxed_turnover_cap}
          baseCap={policy.hard_constraints.max_turnover_pct}
          reason={policy.turnover_relaxation_reason}
        />
      )}

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

      {/* ── Phase 3B.5 — Constraint comparison table ── */}
      {effectiveEnvelope && (
        <ConstraintComparisonTable envelope={effectiveEnvelope} />
      )}

      {/* ── Structured policy violation details (Phase 3B.5) ── */}
      {policy.violation_details && policy.violation_details.length > 0 ? (
        <PolicyViolationList violations={policy.violation_details} />
      ) : (
        <>
          {/* ── Governance flags (legacy string format) ── */}
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

          {/* ── Portfolio violations (legacy) ── */}
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
        </>
      )}

      {/* ── Narrative ── */}
      <p className="text-xs text-gray-500 leading-relaxed border-t border-gray-100 pt-2 mt-1">
        {policy.policy_narrative}
      </p>
    </div>
  );
}
