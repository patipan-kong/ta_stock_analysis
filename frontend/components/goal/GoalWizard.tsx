"use client";

// Phase 4C.3 — Goal Discovery Wizard.
// 5 friendly steps + summary, target completion 1–2 minutes.
// Discovery & personalization only: no projections, no forecasts, no advice.

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { updateGoalProfile } from "@/lib/api";
import type { GoalType, GoalPriority, RiskPersonality } from "@/lib/api";
import {
  GOAL_TYPE_OPTIONS,
  GOAL_PRIORITY_OPTIONS,
  RISK_QUESTION_OPTIONS,
  RISK_PERSONALITY_LABEL_TH,
  formatThaiDate,
  isoDateYearsFromNow,
  fmtBaht,
} from "@/lib/goal";

const AMOUNT_PRESETS = [500_000, 1_000_000, 3_000_000, 5_000_000, 10_000_000];
const YEAR_PRESETS = [1, 3, 5, 10];
const TOTAL_STEPS = 5;

type Step = 0 | 1 | 2 | 3 | 4 | 5; // 5 = summary

export default function GoalWizard({ portfolioId }: { portfolioId: number }) {
  const router = useRouter();
  const [step, setStep] = useState<Step>(0);

  const [goalType, setGoalType] = useState<GoalType | null>(null);
  const [amount, setAmount] = useState<number | null>(null);
  const [customAmount, setCustomAmount] = useState("");
  const [targetDate, setTargetDate] = useState<string | null>(null);
  const [customDate, setCustomDate] = useState("");
  const [priority, setPriority] = useState<GoalPriority | null>(null);
  const [riskKey, setRiskKey] = useState<string | null>(null);

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const riskPersonality: RiskPersonality | null = useMemo(
    () => RISK_QUESTION_OPTIONS.find((o) => o.key === riskKey)?.maps ?? null,
    [riskKey],
  );
  const goalOption = GOAL_TYPE_OPTIONS.find((o) => o.code === goalType);

  const back = () => setStep((s) => (s > 0 ? ((s - 1) as Step) : s));
  const next = () => setStep((s) => (s < 5 ? ((s + 1) as Step) : s));

  const save = async () => {
    if (!goalType) return;
    setSaving(true);
    setError(null);
    try {
      await updateGoalProfile(portfolioId, {
        goal_type: goalType,
        goal_target_value: amount,
        goal_target_date: targetDate,
        goal_priority: priority,
        risk_personality: riskPersonality,
      });
      router.push("/operations-center");
    } catch {
      setError("บันทึกไม่สำเร็จ ลองอีกครั้ง");
      setSaving(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto space-y-5">
      {/* Progress */}
      {step < 5 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-gray-400 tracking-widest uppercase">
            ขั้นตอนที่ {step + 1} จาก {TOTAL_STEPS}
          </p>
          <div className="h-1.5 w-full rounded-full bg-gray-100 overflow-hidden">
            <div
              className="h-full rounded-full bg-gray-900 transition-all duration-300"
              style={{ width: `${((step + 1) / TOTAL_STEPS) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* ── Step 1: goal type ── */}
      {step === 0 && (
        <StepShell title="คุณกำลังลงทุนเพื่ออะไรเป็นหลัก?">
          <div className="grid grid-cols-2 gap-3">
            {GOAL_TYPE_OPTIONS.map((o) => (
              <button
                key={o.code}
                type="button"
                onClick={() => {
                  setGoalType(o.code);
                  next();
                }}
                className={`rounded-2xl border-2 p-4 text-left transition-colors ${
                  goalType === o.code
                    ? "border-gray-900 bg-gray-50"
                    : "border-gray-200 bg-white hover:border-gray-400"
                }`}
              >
                <span className="text-2xl block mb-1">{o.emoji}</span>
                <span className="text-sm font-semibold text-gray-800">{o.label}</span>
              </button>
            ))}
          </div>
        </StepShell>
      )}

      {/* ── Step 2: target amount ── */}
      {step === 1 && (
        <StepShell title="คุณอยากมีเงินถึงเท่าไรสำหรับเป้าหมายนี้?">
          <div className="flex flex-wrap gap-2">
            {AMOUNT_PRESETS.map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => {
                  setAmount(v);
                  setCustomAmount("");
                }}
                className={`rounded-xl border-2 px-4 py-2 text-sm font-semibold transition-colors ${
                  amount === v && customAmount === ""
                    ? "border-gray-900 bg-gray-900 text-white"
                    : "border-gray-200 bg-white text-gray-700 hover:border-gray-400"
                }`}
              >
                {fmtBaht(v)}
              </button>
            ))}
          </div>
          <div className="space-y-1">
            <p className="text-xs text-gray-500">หรือกำหนดเอง</p>
            <input
              type="number"
              min={1}
              value={customAmount}
              onChange={(e) => {
                setCustomAmount(e.target.value);
                const v = parseFloat(e.target.value);
                setAmount(Number.isFinite(v) && v > 0 ? v : null);
              }}
              placeholder="เช่น 2,500,000"
              className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
            />
          </div>
          <WizardNav onBack={back} onNext={next} nextDisabled={amount == null} />
        </StepShell>
      )}

      {/* ── Step 3: target date ── */}
      {step === 2 && (
        <StepShell title="คุณต้องการบรรลุเป้าหมายเมื่อไร?">
          <div className="flex flex-wrap gap-2">
            {YEAR_PRESETS.map((y) => {
              const iso = isoDateYearsFromNow(y);
              const selected = targetDate === iso && customDate === "";
              return (
                <button
                  key={y}
                  type="button"
                  onClick={() => {
                    setTargetDate(iso);
                    setCustomDate("");
                  }}
                  className={`rounded-xl border-2 px-4 py-2 text-sm font-semibold transition-colors ${
                    selected
                      ? "border-gray-900 bg-gray-900 text-white"
                      : "border-gray-200 bg-white text-gray-700 hover:border-gray-400"
                  }`}
                >
                  {y} ปี
                </button>
              );
            })}
          </div>
          <div className="space-y-1">
            <p className="text-xs text-gray-500">หรือกำหนดเอง</p>
            <input
              type="date"
              value={customDate}
              onChange={(e) => {
                setCustomDate(e.target.value);
                setTargetDate(e.target.value || null);
              }}
              className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
            />
          </div>
          {targetDate && (
            <p className="text-xs text-gray-500">
              กำหนดเวลา: <span className="font-semibold text-gray-700">{formatThaiDate(targetDate)}</span>
            </p>
          )}
          <WizardNav onBack={back} onNext={next} nextDisabled={targetDate == null} />
        </StepShell>
      )}

      {/* ── Step 4: priority ── */}
      {step === 3 && (
        <StepShell title="เป้าหมายนี้สำคัญกับคุณแค่ไหน?">
          <div className="space-y-3">
            {GOAL_PRIORITY_OPTIONS.map((o) => (
              <button
                key={o.code}
                type="button"
                onClick={() => {
                  setPriority(o.code);
                  next();
                }}
                className={`w-full rounded-2xl border-2 p-4 text-left transition-colors ${
                  priority === o.code
                    ? "border-gray-900 bg-gray-50"
                    : "border-gray-200 bg-white hover:border-gray-400"
                }`}
              >
                <span className="block text-sm font-bold text-gray-900 tracking-wide">{o.label}</span>
                <span className="block text-xs text-gray-500 mt-0.5">{o.description}</span>
              </button>
            ))}
          </div>
          <WizardNav onBack={back} />
        </StepShell>
      )}

      {/* ── Step 5: risk personality ── */}
      {step === 4 && (
        <StepShell title="หากมูลค่าพอร์ตลดลง 20-30% ในช่วงเวลาสั้น ๆ คุณมีแนวโน้มจะทำอย่างไร?">
          <div className="space-y-3">
            {RISK_QUESTION_OPTIONS.map((o) => (
              <button
                key={o.key}
                type="button"
                onClick={() => {
                  setRiskKey(o.key);
                  next();
                }}
                className={`w-full rounded-2xl border-2 p-4 text-left transition-colors ${
                  riskKey === o.key
                    ? "border-gray-900 bg-gray-50"
                    : "border-gray-200 bg-white hover:border-gray-400"
                }`}
              >
                <span className="block text-sm font-bold text-gray-900">
                  {o.key}. {o.label}
                </span>
                <span className="block text-xs text-gray-500 mt-0.5">{o.hint}</span>
              </button>
            ))}
          </div>
          <WizardNav onBack={back} />
        </StepShell>
      )}

      {/* ── Summary (no projections, no recommendations) ── */}
      {step === 5 && (
        <div className="rounded-2xl border-2 border-gray-200 bg-white p-6 space-y-4 shadow-sm">
          <div className="text-center space-y-1">
            <p className="text-3xl">🎯</p>
            <h2 className="text-lg font-bold text-gray-900">เป้าหมายของคุณ</h2>
            <p className="text-2xl font-bold text-gray-900">
              {goalOption ? `${goalOption.emoji} ${goalOption.label}` : "—"}
            </p>
          </div>
          <div className="divide-y divide-gray-100 text-sm">
            <SummaryRow
              label="เป้าหมาย"
              value={amount != null ? `${amount.toLocaleString("th-TH", { maximumFractionDigits: 0 })} บาท` : "—"}
            />
            <SummaryRow label="กำหนดเวลา" value={formatThaiDate(targetDate)} />
            <SummaryRow
              label="ระดับความสำคัญ"
              value={GOAL_PRIORITY_OPTIONS.find((o) => o.code === priority)?.description ?? "—"}
            />
            <SummaryRow
              label="รูปแบบความเสี่ยง"
              value={riskPersonality ? RISK_PERSONALITY_LABEL_TH[riskPersonality] : "—"}
            />
          </div>
          {error && <p className="text-xs text-red-600 text-center">{error}</p>}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={back}
              className="rounded-xl border border-gray-300 px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-50"
            >
              ← ย้อนกลับ
            </button>
            <button
              type="button"
              onClick={save}
              disabled={saving}
              className="flex-1 rounded-xl bg-gray-900 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50 hover:bg-gray-800 transition-colors"
            >
              {saving ? "กำลังบันทึก…" : "บันทึกเป้าหมาย"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Small building blocks ────────────────────────────────────────────────────

function StepShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border-2 border-gray-200 bg-white p-6 space-y-4 shadow-sm">
      <h2 className="text-base font-bold text-gray-900 leading-relaxed">{title}</h2>
      {children}
    </div>
  );
}

function WizardNav({
  onBack,
  onNext,
  nextDisabled,
}: {
  onBack: () => void;
  onNext?: () => void;
  nextDisabled?: boolean;
}) {
  return (
    <div className="flex items-center justify-between pt-1">
      <button
        type="button"
        onClick={onBack}
        className="text-xs font-medium text-gray-400 hover:text-gray-700"
      >
        ← ย้อนกลับ
      </button>
      {onNext && (
        <button
          type="button"
          onClick={onNext}
          disabled={nextDisabled}
          className="rounded-xl bg-gray-900 px-5 py-2 text-sm font-semibold text-white disabled:opacity-40 hover:bg-gray-800 transition-colors"
        >
          ถัดไป →
        </button>
      )}
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-2.5">
      <span className="text-gray-500">{label}:</span>
      <span className="font-semibold text-gray-900 text-right">{value}</span>
    </div>
  );
}
