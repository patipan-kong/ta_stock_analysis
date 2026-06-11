"use client";

import type { OperationsPolicy } from "@/lib/api";

const CONSTRAINT_LABELS_TH: Record<string, string> = {
  min_cash_pct:            "เงินสดขั้นต่ำ (%)",
  max_single_position_pct: "ถือหุ้นรายตัวสูงสุด (%)",
  max_sector_pct:          "สัดส่วนต่อเซกเตอร์สูงสุด (%)",
  max_turnover_pct:        "เทิร์นโอเวอร์สูงสุด (%)",
  beta_ceiling:            "เพดาน Beta",
  max_new_positions:       "หุ้นใหม่สูงสุด (ตัว)",
  suppress_speculative:    "ระงับหุ้นเก็งกำไร",
};

export default function PolicyEnvelopeCard({ policy }: { policy: OperationsPolicy | null }) {
  if (!policy) {
    return (
      <div className="rounded-2xl border-2 border-gray-200 bg-white p-5 space-y-2 shadow-sm">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
          กรอบนโยบายการลงทุน
        </p>
        <p className="text-sm text-gray-400">
          ยังไม่มีนโยบายที่ใช้งานอยู่ — กรอบนโยบายจะถูกคำนวณในการวิเคราะห์ครั้งถัดไป
        </p>
      </div>
    );
  }

  const constraints = Object.entries(policy.hard_constraints).filter(([, v]) => v != null);

  return (
    <div className="rounded-2xl border-2 border-gray-200 bg-white p-5 space-y-3 shadow-sm">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
          กรอบนโยบายการลงทุน
        </p>
        <div className="flex gap-2">
          {policy.strictness_level && (
            <span className="font-mono text-[10px] font-bold text-gray-600 border border-gray-300 bg-gray-50 px-2 py-0.5 rounded-full">
              {policy.strictness_level}
            </span>
          )}
          {policy.deployment_bias && (
            <span className="font-mono text-[10px] font-bold text-gray-600 border border-gray-300 bg-gray-50 px-2 py-0.5 rounded-full">
              {policy.deployment_bias}
            </span>
          )}
        </div>
      </div>

      {policy.emergency_override && (
        <div className="rounded-xl border-2 border-red-300 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700">
          ⚠ เปิดใช้งานการแทนที่ฉุกเฉิน
          {policy.emergency_reason ? ` — ${policy.emergency_reason}` : ""}
        </div>
      )}

      {policy.violations.length > 0 ? (
        <div className="space-y-1">
          <p className="text-[10px] text-gray-400 uppercase">ข้อจำกัดที่ต้องแก้ไข</p>
          <div className="flex flex-wrap gap-1.5">
            {policy.violations.map((v) => (
              <span
                key={v}
                className="font-mono text-[10px] font-bold text-amber-700 border border-amber-300 bg-amber-50 px-2 py-0.5 rounded-full"
              >
                {v}
              </span>
            ))}
          </div>
        </div>
      ) : (
        <p className="text-xs text-emerald-600 font-semibold">ไม่มีข้อจำกัดที่ต้องแก้ไข</p>
      )}

      {constraints.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {constraints.map(([k, v]) => (
            <div key={k} className="rounded-xl bg-gray-50 px-3 py-2">
              <p className="text-[10px] text-gray-400">{CONSTRAINT_LABELS_TH[k] ?? k}</p>
              <p className="text-sm font-bold text-gray-800">
                {typeof v === "boolean" ? (v ? "เปิด" : "ปิด") : v}
              </p>
            </div>
          ))}
        </div>
      )}

      {policy.policy_narrative && (
        <p className="text-xs text-gray-600 leading-relaxed border-t border-gray-100 pt-2">
          {policy.policy_narrative}
        </p>
      )}
    </div>
  );
}
