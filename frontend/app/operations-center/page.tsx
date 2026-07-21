"use client";

import { useSearchParams } from "next/navigation";
import { usePortfolio } from "@/lib/PortfolioContext";
import OperationsCenter from "@/components/operations-center/OperationsCenter";

export default function OperationsCenterPage() {
  const { currentSelection, loading } = usePortfolio();
  const searchParams = useSearchParams();

  const symbolsParam = searchParams.get("symbols");
  const initialSymbols = symbolsParam
    ? symbolsParam.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean)
    : undefined;

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
      <OperationsCenter portfolioId={currentSelection} initialSymbols={initialSymbols} />
    </div>
  );
}
