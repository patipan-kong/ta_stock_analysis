"use client";

// Phase 4C.3 — Goal Discovery Wizard route.
// Lightweight onboarding for the active portfolio; reached from the
// MUJI-mode Goal Profile card in ศูนย์บัญชาการ AI.

import { usePortfolio } from "@/lib/PortfolioContext";
import BackBreadcrumb from "@/components/BackBreadcrumb";
import GoalWizard from "@/components/goal/GoalWizard";

export default function GoalWizardPage() {
  const { currentSelection, loading } = usePortfolio();

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8 text-sm text-gray-500">
        กำลังโหลดพอร์ต…
      </div>
    );
  }

  if (currentSelection == null) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="rounded-2xl border-2 border-gray-200 bg-white p-8 text-center text-gray-500">
          ยังไม่มีพอร์ต — สร้างพอร์ตแรกได้ที่หน้า &ldquo;พอร์ตโฟลิโอ&rdquo;
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <BackBreadcrumb
        parent="ศูนย์บัญชาการ AI"
        current="ตั้งเป้าหมายการลงทุน"
        href="/operations-center"
      />
      <GoalWizard portfolioId={currentSelection} />
    </div>
  );
}
