"use client";

import type { SystemHealth } from "@/lib/api";
import {
  fmtMs, fmtInt, fmtUsd, fmtPct01, fmtAgeMinutes, fmtTimestamp,
  latencyHealth, fallbackHealth, ageHealth,
  invertedBooleanHealth, schedulerRunHealth, policyEngineHealth,
  type HealthLevel,
} from "@/lib/ai-analytics-transformers";
import { ReliabilityMetricCard } from "./shared";

// Extensibility: each group below is just an array of { label, value, level, sub }
// built from real SystemHealth fields. To add a new component (Symbol Resolver,
// Cache, Event Bus, ...) push another group here — no layout change required.
// Unavailable signals must stay `level: "unknown"` / `value: null` rather than
// being guessed at; ReliabilityMetricCard renders that as N/A automatically.

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{title}</p>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">{children}</div>
    </div>
  );
}

export default function SystemHealthSection({ health }: { health: SystemHealth }) {
  const opt = health.optimizer_pipeline;
  const md = health.market_data;
  const pe = health.portfolio_engine;
  const bg = health.background_jobs;
  const om = health.optional_metrics;
  const rel = health.prompt_pipeline;

  const policyLevel = policyEngineHealth(opt.policy_engine_status);

  return (
    <div className="space-y-5">
      {policyLevel === "problem" && (
        <div className="text-xs px-3 py-2 rounded border text-red-700 bg-red-50 border-red-200">
          🔴 Policy Engine Disabled (Fallback Mode) — the most recent optimizer run used
          legacy regime-only constraints. Persona weighting, confidence-adjusted limits, and
          policy alignment scoring were skipped. Check backend logs for{" "}
          <span className="font-mono">[POLICY_ENGINE]</span> errors.
        </div>
      )}

      {/* ── AI Providers ── */}
      <Group title="AI Providers">
        {health.ai_providers.map((p) => {
          // Not configured: neutral, not alarming (may be an intentionally unused backup).
          // Configured + used in the last 24h: healthy. Configured + no calls today but has
          // succeeded before: idle, not a failure. Configured but never once succeeded: worth flagging.
          const level: HealthLevel = !p.configured
            ? "unknown"
            : p.call_count_24h > 0
              ? "healthy"
              : p.last_success_at != null
                ? "unknown"
                : "warning";
          return (
            <ReliabilityMetricCard
              key={p.provider}
              label={p.provider.toUpperCase()}
              value={p.configured ? fmtTimestamp(p.last_success_at) : "Not configured"}
              level={level}
              sub={
                p.configured
                  ? `${fmtInt(p.call_count_24h)} calls / 24h · avg ${fmtMs(p.avg_latency_ms_24h)}`
                  : "No API key set for this provider"
              }
            />
          );
        })}
      </Group>

      {/* ── Optimizer Pipeline ── */}
      <Group title="Optimizer Pipeline">
        <ReliabilityMetricCard
          label="L1 Optimizer"
          value={fmtMs(opt.layer1_latency_ms)}
          level={invertedBooleanHealth(opt.layer1_error)}
          sub={opt.layer1_error ? "Last run reported an error" : "Latency, last run"}
        />
        <ReliabilityMetricCard
          label="L2 Challenger"
          value={fmtMs(opt.layer2_latency_ms)}
          level={invertedBooleanHealth(opt.layer2_error)}
          sub={opt.layer2_error ? "Last run reported an error" : "Latency, last run"}
        />
        <ReliabilityMetricCard
          label="L3 Auditor"
          value={fmtMs(opt.layer3_latency_ms)}
          level={invertedBooleanHealth(opt.layer3_error)}
          sub={opt.layer3_error ? "Last run reported an error" : "Latency, last run"}
        />
        <ReliabilityMetricCard
          label="Global Fallback"
          value={opt.fallback_mode == null ? "N/A" : opt.fallback_mode ? "Running on fallback only" : "Not triggered"}
          level={invertedBooleanHealth(opt.fallback_mode)}
          sub={opt.last_run_at ? `Last run ${fmtTimestamp(opt.last_run_at)}` : "No optimizer run recorded yet"}
        />
      </Group>

      {/* ── Policy Engine ── */}
      <Group title="Policy Engine">
        <ReliabilityMetricCard
          label="Policy Engine"
          value={
            opt.policy_engine_status === "ACTIVE" ? "Active" :
            opt.policy_engine_status === "DISABLED_FALLBACK" ? "Disabled (Fallback Mode)" : "Unknown"
          }
          level={policyLevel}
          sub={opt.last_run_at ? `Last run ${fmtTimestamp(opt.last_run_at)}` : "No optimizer run recorded yet"}
        />
      </Group>

      {/* ── Market Data ── */}
      <Group title="Market Data">
        <ReliabilityMetricCard
          label="Latest Market Update"
          value={fmtAgeMinutes(md.age_minutes)}
          level={ageHealth(md.age_minutes)}
          sub={md.latest_update_at ? fmtTimestamp(md.latest_update_at) : "No price sync recorded yet"}
        />
        <ReliabilityMetricCard
          label="Sync Errors"
          value={fmtInt(md.sync_status_counts.error)}
          level={invertedBooleanHealth(md.sync_status_counts.error > 0)}
          sub={`${fmtInt(md.sync_status_counts.ok)} ok · ${fmtInt(md.sync_status_counts.stale)} stale`}
        />
      </Group>

      {/* ── Portfolio Engine ── */}
      <Group title="Portfolio Engine">
        <ReliabilityMetricCard
          label="Snapshot Engine"
          value={pe.snapshot_scheduler_status ?? "Unknown"}
          level={pe.snapshot_scheduler_status ? schedulerRunHealth(pe.snapshot_scheduler_status) : "unknown"}
          sub={pe.last_snapshot_at ? `Last snapshot ${fmtTimestamp(pe.last_snapshot_at)}` : "Not tracked yet"}
        />
        <ReliabilityMetricCard label="Replay Engine" value="N/A" level="unknown" sub="No runtime health signal tracked yet" />
        <ReliabilityMetricCard label="Calculation Engine" value="N/A" level="unknown" sub="No runtime health signal tracked yet" />
      </Group>

      {/* ── Prompt / AI Pipeline — reuses the existing Reliability metrics, not recomputed ── */}
      <Group title="Prompt / AI Pipeline">
        <ReliabilityMetricCard
          label="Fallback Rate"
          value={fmtPct01(rel.fallback_rate)}
          level={fallbackHealth(rel.fallback_rate)}
          sub="Share of optimizer calls that hit the global fallback model"
        />
        <ReliabilityMetricCard label="JSON Parser" value="N/A" level="unknown" sub="Not tracked yet" />
        <ReliabilityMetricCard label="Response Validation" value="N/A" level="unknown" sub="Not tracked yet" />
      </Group>

      {/* ── Background Jobs ── */}
      <Group title="Background Jobs">
        <ReliabilityMetricCard
          label="Snapshot Scheduler"
          value={bg.snapshot_scheduler.status ?? "Unknown"}
          level={bg.snapshot_scheduler.status ? schedulerRunHealth(bg.snapshot_scheduler.status) : "unknown"}
          sub={bg.snapshot_scheduler.last_run_at ? `Last run ${fmtTimestamp(bg.snapshot_scheduler.last_run_at)}` : "Not run in this process yet"}
        />
        <ReliabilityMetricCard
          label="Market Update"
          value={fmtAgeMinutes(md.age_minutes)}
          level={ageHealth(md.age_minutes)}
          sub={bg.market_update.note}
        />
        <ReliabilityMetricCard label="Reminder Jobs" value="N/A" level="unknown" sub={bg.reminders.note} />
      </Group>

      {/* ── Optional Metrics ── */}
      <Group title="Today at a Glance">
        <ReliabilityMetricCard label="AI Requests Today" value={fmtInt(om.requests_today)} level={"unknown" as HealthLevel} sub="Informational only" />
        <ReliabilityMetricCard label="Avg Latency" value={fmtMs(om.avg_latency_ms_today)} level={latencyHealth(om.avg_latency_ms_today)} sub="Today, all providers" />
        <ReliabilityMetricCard label="Avg Cost / Request" value={fmtUsd(om.avg_cost_usd_today, 5)} level={"unknown" as HealthLevel} sub="Today, all providers" />
        <ReliabilityMetricCard label="Failure Rate" value="N/A" level="unknown" sub="Not tracked yet" />
      </Group>
    </div>
  );
}
