"use client";

import Link from "next/link";
import type { MujiAction } from "@/lib/api";
import { optimizerFreshnessTh } from "../freshness";

const SEVERITY_CFG: Record<
  MujiAction["severity"],
  { bg: string; border: string; text: string; icon: string; title: string }
> = {
  INFO: {
    bg: "bg-emerald-50",
    border: "border-emerald-200",
    text: "text-emerald-800",
    icon: "🟢",
    title: "ทุกอย่างเรียบร้อย",
  },
  WARN: {
    bg: "bg-amber-50",
    border: "border-amber-200",
    text: "text-amber-800",
    icon: "🟡",
    title: "มีเรื่องที่ควรดู",
  },
  ACTION: {
    bg: "bg-blue-50",
    border: "border-blue-200",
    text: "text-blue-800",
    icon: "🔵",
    title: "แนะนำให้ดำเนินการ",
  },
};

export default function ActionCard({
  action,
  lastRunAt,
  optimizing,
  onRunOptimizer,
}: {
  action: MujiAction;
  lastRunAt: string | null;
  optimizing: boolean;
  onRunOptimizer: () => void;
}) {
  const neverRun = lastRunAt == null;
  const cfg = SEVERITY_CFG[action.severity] ?? SEVERITY_CFG.INFO;

  // Never-analyzed state: dedicated headline + first-run call to action.
  if (neverRun) {
    return (
      <div className="rounded-2xl border-2 border-blue-200 bg-blue-50 p-5 space-y-3 shadow-sm">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
          สิ่งที่ควรทำ
        </p>
        <div className="flex items-start gap-3">
          <span className="text-2xl leading-none">🔵</span>
          <div className="space-y-2">
            <p className="text-sm font-bold text-blue-800">เริ่มสร้างแผนการลงทุนของคุณ</p>
            <p className="text-sm text-gray-700">
              รับคำแนะนำการจัดพอร์ตที่เหมาะสมกับสถานการณ์ตลาดและเป้าหมายของคุณ
            </p>
            <div className="flex items-center gap-4 flex-wrap mt-1">
              <button
                onClick={onRunOptimizer}
                disabled={optimizing}
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {optimizing ? "กำลังวิเคราะห์…" : "🪄 สร้างแผนการลงทุน"}
              </button>
              <Link href="/optimizer" className="text-sm font-semibold text-blue-700 underline">
                ดูแผนการลงทุน →
              </Link>
            </div>
            <p className="text-[11px] text-gray-400">{optimizerFreshnessTh(lastRunAt)}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`rounded-2xl border-2 ${cfg.border} ${cfg.bg} p-5 space-y-2 shadow-sm`}>
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
        สิ่งที่ควรทำ
      </p>
      <div className="flex items-start gap-3">
        <span className="text-2xl leading-none">{cfg.icon}</span>
        <div className="space-y-2">
          <p className={`text-sm font-bold ${cfg.text}`}>{cfg.title}</p>
          <p className="text-sm text-gray-700">{action.action_th}</p>
          <div className="flex items-center gap-4 flex-wrap mt-1">
            <button
              onClick={onRunOptimizer}
              disabled={optimizing}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {optimizing ? "กำลังวิเคราะห์…" : "🪄 อัปเดตมุมมองพอร์ต"}
            </button>
            <Link href={action.link ?? "/optimizer"} className="text-sm font-semibold text-blue-700 underline">
              ดูคำแนะนำล่าสุด →
            </Link>
          </div>
          <p className="text-[11px] text-gray-400">{optimizerFreshnessTh(lastRunAt)}</p>
        </div>
      </div>
    </div>
  );
}
