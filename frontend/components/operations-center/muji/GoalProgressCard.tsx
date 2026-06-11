"use client";

import { useState } from "react";
import { updatePortfolioGoal } from "@/lib/api";

const fmtBaht = (v: number) =>
  `฿${v.toLocaleString("th-TH", { maximumFractionDigits: 0 })}`;

export default function GoalProgressCard({
  portfolioId,
  portfolioValue,
  goalTargetValue,
  goalProgressPct,
  onSaved,
}: {
  portfolioId: number;
  portfolioValue: number | null;
  goalTargetValue: number | null;
  goalProgressPct: number | null;
  onSaved: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [input, setInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    const value = parseFloat(input.replace(/,/g, ""));
    if (!Number.isFinite(value) || value <= 0) {
      setError("กรุณาใส่จำนวนเงินที่มากกว่า 0");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await updatePortfolioGoal(portfolioId, value);
      setEditing(false);
      setInput("");
      onSaved();
    } catch {
      setError("บันทึกไม่สำเร็จ ลองอีกครั้ง");
    } finally {
      setSaving(false);
    }
  };

  const showForm = goalTargetValue == null || editing;
  const pct = goalProgressPct != null ? Math.min(100, Math.max(0, goalProgressPct)) : null;

  return (
    <div className="rounded-2xl border-2 border-gray-200 bg-white p-5 space-y-3 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
          เป้าหมายของคุณ
        </p>
        {goalTargetValue != null && !editing && (
          <button
            type="button"
            onClick={() => {
              setInput(String(goalTargetValue));
              setEditing(true);
            }}
            className="text-xs text-gray-400 hover:text-gray-700 underline"
          >
            แก้ไข
          </button>
        )}
      </div>

      {showForm ? (
        <div className="space-y-2">
          <p className="text-sm text-gray-600">
            ตั้งเป้าหมายมูลค่าพอร์ต แล้วระบบจะติดตามความคืบหน้าให้คุณ
          </p>
          <div className="flex gap-2">
            <input
              type="number"
              min={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="เช่น 1,000,000"
              className="flex-1 rounded-xl border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
            />
            <button
              type="button"
              onClick={save}
              disabled={saving}
              className="rounded-xl bg-gray-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {saving ? "กำลังบันทึก…" : "บันทึก"}
            </button>
            {editing && (
              <button
                type="button"
                onClick={() => {
                  setEditing(false);
                  setError(null);
                }}
                className="rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-600"
              >
                ยกเลิก
              </button>
            )}
          </div>
          {error && <p className="text-xs text-red-600">{error}</p>}
        </div>
      ) : (
        <div className="space-y-2">
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-gray-900">
              {pct != null ? `${pct.toFixed(1)}%` : "—"}
            </p>
            <p className="text-xs text-gray-500">
              {portfolioValue != null ? fmtBaht(portfolioValue) : "—"} /{" "}
              {fmtBaht(goalTargetValue as number)}
            </p>
          </div>
          <div className="h-3 w-full rounded-full bg-gray-100 overflow-hidden">
            <div
              className="h-full rounded-full bg-emerald-500 transition-all"
              style={{ width: `${pct ?? 0}%` }}
            />
          </div>
          <p className="text-[11px] text-gray-400">
            {pct == null
              ? "รอข้อมูลมูลค่าพอร์ตเพื่อคำนวณความคืบหน้า"
              : pct >= 100
                ? "ยินดีด้วย! คุณถึงเป้าหมายแล้ว 🎉"
                : `อีก ${fmtBaht(Math.max(0, (goalTargetValue as number) - (portfolioValue ?? 0)))} จะถึงเป้าหมาย`}
          </p>
        </div>
      )}
    </div>
  );
}
