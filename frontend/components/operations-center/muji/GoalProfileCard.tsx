"use client";

// Phase 4C.3 — Goal Profile card (MUJI mode).
// Displays what the user is investing for; links to the Goal Discovery
// Wizard when nothing is configured yet. Display only — no projections.

import Link from "next/link";
import type { GoalProfile } from "@/lib/api";
import { formatThaiDate, fmtBaht } from "@/lib/goal";

export default function GoalProfileCard({ profile }: { profile: GoalProfile }) {
  if (!profile.configured) {
    return (
      <div className="rounded-2xl border-2 border-dashed border-gray-200 bg-gray-50 p-6 space-y-3">
        <div className="text-center space-y-1.5">
          <p className="text-base font-semibold text-gray-800">
            เริ่มต้นด้วยการกำหนดเป้าหมายการลงทุนของคุณ
          </p>
          <p className="text-xs text-gray-500 max-w-xs mx-auto leading-relaxed">
            เป้าหมายจะช่วยให้ระบบติดตามความคืบหน้าและสรุปผลได้ชัดเจนขึ้น
          </p>
        </div>
        <div className="flex justify-center">
          <Link
            href="/goal-wizard"
            className="inline-block rounded-xl bg-gray-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-gray-800 transition-colors"
          >
            🎯 เริ่มตั้งเป้าหมาย
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border-2 border-gray-200 bg-white p-5 space-y-3 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
          🎯 เป้าหมายการลงทุน
        </p>
        <Link href="/goal-wizard" className="text-xs text-gray-400 hover:text-gray-700 underline">
          แก้ไข
        </Link>
      </div>

      <p className="text-xl font-bold text-gray-900">
        {profile.goal_emoji} {profile.goal_label_th}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
        <div>
          <p className="text-[11px] text-gray-400">เป้าหมาย</p>
          <p className="font-semibold text-gray-800">
            {profile.goal_target_value != null ? fmtBaht(profile.goal_target_value) : "—"}
          </p>
        </div>
        <div>
          <p className="text-[11px] text-gray-400">กำหนดเวลา</p>
          <p className="font-semibold text-gray-800">{formatThaiDate(profile.goal_target_date)}</p>
        </div>
        <div>
          <p className="text-[11px] text-gray-400">ระดับความสำคัญ</p>
          <p className="font-semibold text-gray-800">
            {profile.goal_priority_label_th ?? "—"}
          </p>
        </div>
      </div>

      {profile.risk_personality_label_th && (
        <p className="text-[11px] text-gray-400">
          รูปแบบความเสี่ยงของคุณ:{" "}
          <span className="font-semibold text-gray-600">{profile.risk_personality_label_th}</span>
        </p>
      )}
    </div>
  );
}
