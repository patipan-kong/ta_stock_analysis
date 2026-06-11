"use client";

import Link from "next/link";
import type { OperationsOptimizer } from "@/lib/api";
import { optimizerFreshnessTh, contextualGuidanceTh } from "../freshness";

const DECISION_CFG: Record<string, { text: string; badge: string; label_th: string }> = {
  NO_ACTION: { text: "text-emerald-700", badge: "bg-emerald-100 border-emerald-300", label_th: "ไม่ต้องดำเนินการ" },
  REVIEW:    { text: "text-amber-700",   badge: "bg-amber-100 border-amber-300",    label_th: "รอตรวจสอบ" },
  REBALANCE: { text: "text-blue-700",    badge: "bg-blue-100 border-blue-300",      label_th: "ควรปรับสัดส่วน" },
};

const RISK_LABEL_TH: Record<string, string> = {
  low:    "ต่ำ",
  medium: "ปานกลาง",
  high:   "สูง",
};

const OPTIMIZER_STATUS_TH: Record<string, string> = {
  REBALANCE: "ควรปรับสัดส่วน",
  NO_ACTION: "ไม่ต้องดำเนินการ",
};

export default function ConsensusRoomCard({
  optimizer,
  optimizing,
  onRunOptimizer,
  daysSinceRebalance,
}: {
  optimizer: OperationsOptimizer;
  optimizing: boolean;
  onRunOptimizer: () => void;
  daysSinceRebalance: number | null;
}) {
  const score = optimizer.consensus_score;
  const decision = optimizer.consensus_decision;
  const cfg = decision ? (DECISION_CFG[decision] ?? DECISION_CFG.NO_ACTION) : null;
  const guidance = contextualGuidanceTh(optimizer.last_run_at, daysSinceRebalance);

  const runButton = (
    <button
      onClick={onRunOptimizer}
      disabled={optimizing}
      className="inline-flex items-center gap-1.5 rounded-lg border border-gray-900 bg-gray-900 px-3 py-1.5 font-mono text-xs font-bold text-white hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
    >
      {optimizing ? "กำลังวิเคราะห์…" : "⚡ วิเคราะห์พอร์ต"}
    </button>
  );

  // ── Empty state: never analyzed ─────────────────────────────────────────────
  if (!optimizer.last_run_at) {
    return (
      <div className="rounded-2xl border-2 border-gray-200 bg-white p-5 space-y-3 shadow-sm">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
          ห้องประชุม AI
        </p>
        <div className="space-y-1">
          <p className="text-base font-bold text-gray-800">ยังไม่เคยวิเคราะห์พอร์ตนี้</p>
          <p className="text-sm text-gray-500">
            เริ่มต้นด้วยการวิเคราะห์พอร์ต เพื่อให้ AI ช่วยประเมินสถานการณ์ปัจจุบัน
          </p>
        </div>
        <div className="flex items-center justify-between gap-3 flex-wrap">
          {runButton}
          <Link href="/optimizer" className="font-mono text-[11px] font-semibold text-blue-600 hover:underline">
            เปิดหน้า Optimizer →
          </Link>
        </div>
        <p className="text-[11px] text-gray-400">{optimizerFreshnessTh(null)}</p>
      </div>
    );
  }

  // ── Populated state ──────────────────────────────────────────────────────────
  return (
    <div className="rounded-2xl border-2 border-gray-200 bg-white p-5 space-y-3 shadow-sm">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
          ห้องประชุม AI
        </p>
        {decision && cfg && (
          <span
            className={`font-mono text-[10px] font-bold border px-2 py-0.5 rounded-full ${cfg.badge} ${cfg.text}`}
          >
            {cfg.label_th}
          </span>
        )}
      </div>

      <p className="text-lg font-bold text-gray-900">{optimizer.consensus_status ?? "—"}</p>

      {/* Strength gauge */}
      <div className="space-y-1">
        <div className="flex justify-between text-[10px] text-gray-400 uppercase">
          <span>ความเห็นพ้อง</span>
          <span>{score != null ? `${score}/100` : "—"}</span>
        </div>
        <div className="h-2.5 w-full rounded-full bg-gray-100 overflow-hidden">
          <div
            className={`h-full rounded-full ${
              score == null
                ? "bg-gray-300"
                : score >= 70
                  ? "bg-emerald-500"
                  : score >= 40
                    ? "bg-amber-400"
                    : "bg-red-500"
            }`}
            style={{ width: `${Math.min(100, Math.max(0, score ?? 0))}%` }}
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-gray-500">
        {optimizer.final_risk_level && (
          <span>
            ความเสี่ยง:{" "}
            <span className="font-semibold text-gray-700">
              {RISK_LABEL_TH[optimizer.final_risk_level.toLowerCase()] ?? optimizer.final_risk_level}
            </span>
          </span>
        )}
        {optimizer.optimizer_status && (
          <span>
            สถานะ:{" "}
            <span className="font-semibold text-gray-700">
              {OPTIMIZER_STATUS_TH[optimizer.optimizer_status] ?? optimizer.optimizer_status}
            </span>
          </span>
        )}
      </div>

      {optimizer.recommended_action && (
        <p className="text-xs text-gray-600 leading-relaxed border-t border-gray-100 pt-2">
          {optimizer.recommended_action}
        </p>
      )}

      {/* Contextual guidance (Task 4) */}
      {guidance && (
        <p className="text-xs text-blue-700 bg-blue-50 rounded-lg px-3 py-2">{guidance}</p>
      )}

      <div className="flex items-center justify-between gap-3 border-t border-gray-100 pt-3 flex-wrap">
        <div className="flex items-center gap-3">
          {runButton}
          <Link href="/optimizer" className="font-mono text-[11px] font-semibold text-blue-600 hover:underline whitespace-nowrap">
            เปิดหน้า Optimizer →
          </Link>
        </div>
        <span className="text-[11px] text-gray-400">
          {optimizerFreshnessTh(optimizer.last_run_at)}
        </span>
      </div>
    </div>
  );
}
