// Goal Discovery Wizard vocabulary (Phase 4C.3).
// Mirrors backend services/goal_profile.py — codes are stored, labels are display.

import type { GoalType, GoalPriority, RiskPersonality } from "@/lib/api";

export const GOAL_TYPE_OPTIONS: { code: GoalType; emoji: string; label: string }[] = [
  { code: "WEDDING", emoji: "💍", label: "งานแต่งงาน" },
  { code: "HOUSE", emoji: "🏠", label: "ซื้อบ้าน" },
  { code: "EDUCATION", emoji: "👶", label: "การศึกษา" },
  { code: "RETIREMENT", emoji: "🌴", label: "เกษียณ" },
  { code: "FINANCIAL_FREEDOM", emoji: "💰", label: "อิสรภาพทางการเงิน" },
  { code: "WEALTH_GROWTH", emoji: "🚀", label: "สร้างความมั่งคั่งระยะยาว" },
  { code: "OTHER", emoji: "✨", label: "เป้าหมายอื่น" },
];

export const GOAL_PRIORITY_OPTIONS: {
  code: GoalPriority;
  label: string;
  description: string;
}[] = [
  { code: "ESSENTIAL", label: "ESSENTIAL", description: "จำเป็นต้องสำเร็จตามกำหนด" },
  { code: "IMPORTANT", label: "IMPORTANT", description: "สำคัญมาก แต่ยืดหยุ่นได้บ้าง" },
  { code: "ASPIRATIONAL", label: "ASPIRATIONAL", description: "เป็นความฝันหรือเป้าหมายระยะยาว" },
];

// Wizard answers A–D map to 3 risk personalities.
export const RISK_QUESTION_OPTIONS: {
  key: string;
  label: string;
  hint: string;
  maps: RiskPersonality;
}[] = [
  { key: "A", label: "ซื้อเพิ่ม", hint: "มองว่าเป็นโอกาสซื้อของถูก", maps: "AGGRESSIVE" },
  { key: "B", label: "ถือไว้ตามแผน", hint: "ไม่ตื่นตระหนก เชื่อในแผนระยะยาว", maps: "MODERATE" },
  { key: "C", label: "ขายบางส่วน", hint: "ลดความเสี่ยงลงให้สบายใจขึ้น", maps: "CONSERVATIVE" },
  { key: "D", label: "ขายทั้งหมด", hint: "ไม่อยากเห็นเงินลดลงไปมากกว่านี้", maps: "CONSERVATIVE" },
];

export const RISK_PERSONALITY_LABEL_TH: Record<RiskPersonality, string> = {
  AGGRESSIVE: "เชิงรุก",
  MODERATE: "ปานกลาง",
  CONSERVATIVE: "ระมัดระวัง",
};

const TH_MONTHS = [
  "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
  "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
];

/** "2026-12-12" → "12 ธันวาคม 2026" (CE year, matching the rest of the app). */
export function formatThaiDate(iso: string | null): string {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d || m < 1 || m > 12) return iso;
  return `${d} ${TH_MONTHS[m - 1]} ${y}`;
}

/** ISO date exactly N years from today (local time). */
export function isoDateYearsFromNow(years: number): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() + years);
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mm}-${dd}`;
}

export const fmtBaht = (v: number) =>
  `฿${v.toLocaleString("th-TH", { maximumFractionDigits: 0 })}`;
