// ── Optimizer freshness ──────────────────────────────────────────────────────

/** Thai relative-time freshness label for the last optimizer run. */
export function optimizerFreshnessTh(lastRunAt: string | null): string {
  if (!lastRunAt) return "ยังไม่เคยวิเคราะห์";
  const ms = Date.now() - new Date(lastRunAt).getTime();
  if (!Number.isFinite(ms) || ms < 0) return "ยังไม่เคยวิเคราะห์";
  const minutes = Math.floor(ms / 60_000);
  if (minutes < 1) return "วิเคราะห์ล่าสุดเมื่อสักครู่";
  if (minutes < 60) return `วิเคราะห์ล่าสุด ${minutes} นาทีที่แล้ว`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `วิเคราะห์ล่าสุด ${hours} ชั่วโมงที่แล้ว`;
  const days = Math.floor(hours / 24);
  return `วิเคราะห์ล่าสุด ${days} วันที่แล้ว`;
}

/** Friendly Thai label used as a compact "last analysis" badge.
 *  Relative for <24h, absolute date-time otherwise. */
export function optimizerLastAnalysisBadgeTh(lastRunAt: string | null): string {
  if (!lastRunAt) return "วิเคราะห์ล่าสุด: ยังไม่เคยวิเคราะห์";
  const ts = new Date(lastRunAt);
  const diffMs = Date.now() - ts.getTime();
  if (!Number.isFinite(diffMs) || diffMs < 0) {
    return "วิเคราะห์ล่าสุด: ยังไม่เคยวิเคราะห์";
  }

  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return "วิเคราะห์ล่าสุด: สักครู่ก่อน";
  if (minutes < 60) return `วิเคราะห์ล่าสุด: ${minutes} นาทีที่แล้ว`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `วิเคราะห์ล่าสุด: ${hours} ชั่วโมงก่อน`;

  const absolute = ts.toLocaleString("th-TH", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Bangkok",
  });
  return `วิเคราะห์ล่าสุด: ${absolute}`;
}

/** True when the last run is old enough that a fresh analysis is worth suggesting. */
export function isAnalysisStale(lastRunAt: string | null, staleDays = 3): boolean {
  if (!lastRunAt) return true;
  const ms = Date.now() - new Date(lastRunAt).getTime();
  return Number.isFinite(ms) && ms > staleDays * 24 * 60 * 60 * 1000;
}

// ── Market data freshness ─────────────────────────────────────────────────────

/** Thai freshness label for portfolio snapshot / market data, given a YYYY-MM-DD date string. */
export function marketDataFreshnessTh(snapshotDate: string | null): string {
  if (!snapshotDate) return "ยังไม่มีข้อมูลตลาด";
  // Compare calendar days in Bangkok time (treat date-only as local midnight).
  const snap = new Date(snapshotDate + "T00:00:00");
  const diffMs = Date.now() - snap.getTime();
  if (!Number.isFinite(diffMs) || diffMs < 0) return "ยังไม่มีข้อมูลตลาด";
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (days === 0) return "ข้อมูลตลาดอัปเดตวันนี้";
  if (days === 1) return "ข้อมูลตลาดอัปเดตเมื่อวานนี้";
  return `ข้อมูลตลาดอัปเดตเมื่อ ${days} วันที่แล้ว`;
}

/** Friendly Thai text for time since last rebalance. */
export function rebalanceFreshnessTh(daysSinceLastRebalance: number | null): string {
  if (daysSinceLastRebalance == null) return "ยังไม่มีประวัติการรีบาลานซ์";
  if (daysSinceLastRebalance === 0) return "รีบาลานซ์ล่าสุด: วันนี้";
  if (daysSinceLastRebalance === 1) return "รีบาลานซ์ล่าสุด: เมื่อวาน";
  return `รีบาลานซ์ล่าสุด: ${daysSinceLastRebalance} วันที่แล้ว`;
}

/** True when market data (snapshot) is stale beyond the given threshold.
 *  Threshold defaults to 2 days — weekends are ignored by design; keep it simple. */
export function isMarketDataStale(snapshotDate: string | null, staleDays = 2): boolean {
  if (!snapshotDate) return true;
  const snap = new Date(snapshotDate + "T00:00:00");
  const days = Math.floor((Date.now() - snap.getTime()) / (1000 * 60 * 60 * 24));
  return days > staleDays;
}

// ── Contextual guidance ──────────────────────────────────────────────────────

/** Lightweight guidance hint for the user based on optimizer run age and rebalance history.
 *  Returns null when no hint is worth showing (e.g. moderate 1-7 day range). */
export function contextualGuidanceTh(
  lastRunAt: string | null,
  daysSinceRebalance: number | null,
): string | null {
  if (!lastRunAt) return "เริ่มวิเคราะห์ครั้งแรกเพื่อดูภาพรวมของพอร์ต";
  if (daysSinceRebalance === 0) return "พอร์ตเพิ่งได้รับการปรับสัดส่วนล่าสุด";
  const ms = Date.now() - new Date(lastRunAt).getTime();
  const hours = ms / (1000 * 60 * 60);
  if (hours < 24) return "เพิ่งวิเคราะห์พอร์ตไม่นาน อาจยังไม่จำเป็นต้องรันใหม่";
  if (hours / 24 > 7) return "ไม่ได้วิเคราะห์พอร์ตมาหลายวันแล้ว อาจลองอัปเดตคำแนะนำอีกครั้ง";
  return null;
}
