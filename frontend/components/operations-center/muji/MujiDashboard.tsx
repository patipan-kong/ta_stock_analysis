"use client";

import type { OperationsCenterStatus } from "@/lib/api";
import GoalProfileCard from "./GoalProfileCard";
import GoalProgressCard from "./GoalProgressCard";
import MujiSummaryCard from "./MujiSummaryCard";
import ActionCard from "./ActionCard";

const fmtBaht = (v: number) =>
  `฿${v.toLocaleString("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function MujiDashboard({
  status,
  portfolioId,
  onGoalSaved,
  optimizing,
  onRunOptimizer,
}: {
  status: OperationsCenterStatus;
  portfolioId: number;
  onGoalSaved: () => void;
  optimizing: boolean;
  onRunOptimizer: () => void;
}) {
  const s = status.portfolio_summary;
  const change = s.daily_return_pct;
  const changeColor =
    change == null ? "text-gray-400" : change >= 0 ? "text-emerald-600" : "text-red-600";

  return (
    <div className="space-y-4">
      {/* Hero: portfolio value + today's change */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-2xl border-2 border-gray-200 bg-white p-5 space-y-1 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
            มูลค่าพอร์ตวันนี้
          </p>
          <p className="text-3xl font-bold text-gray-900">
            {s.portfolio_value != null ? fmtBaht(s.portfolio_value) : "—"}
          </p>
          {s.snapshot_date && (
            <p className="text-[11px] text-gray-400">ข้อมูล ณ วันที่ {s.snapshot_date}</p>
          )}
        </div>
        <div className="rounded-2xl border-2 border-gray-200 bg-white p-5 space-y-1 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
            การเปลี่ยนแปลงวันนี้
          </p>
          <p className={`text-3xl font-bold ${changeColor}`}>
            {change != null ? `${change >= 0 ? "+" : ""}${change.toFixed(2)}%` : "—"}
          </p>
          <p className="text-[11px] text-gray-400">
            {change == null
              ? "ยังไม่มีข้อมูลผลตอบแทนรายวัน"
              : change >= 0
                ? "พอร์ตของคุณเติบโตขึ้นวันนี้"
                : "พอร์ตของคุณลดลงเล็กน้อยวันนี้"}
          </p>
        </div>
      </div>

      {/* Phase 4C.3 — what the user is investing for (wizard data, display only) */}
      <GoalProfileCard profile={status.goal_profile} />

      <GoalProgressCard
        portfolioId={portfolioId}
        portfolioValue={s.portfolio_value}
        goalTargetValue={s.goal_target_value}
        goalProgressPct={s.goal_progress_pct}
        onSaved={onGoalSaved}
      />

      <MujiSummaryCard translation={status.muji_translation} />

      <ActionCard
        action={status.muji_translation.action_required}
        lastRunAt={status.optimizer.last_run_at}
        optimizing={optimizing}
        onRunOptimizer={onRunOptimizer}
      />
    </div>
  );
}
