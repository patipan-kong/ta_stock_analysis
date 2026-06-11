"use client";

import type { OperationsMode } from "@/lib/api";

const OPTIONS: { value: OperationsMode; label: string; hint: string }[] = [
  { value: "MUJI", label: "MUJI", hint: "มุมมองแบบเรียบง่าย" },
  { value: "QUANT", label: "QUANT", hint: "Full operations view" },
];

export default function ModeToggle({
  mode,
  onChange,
}: {
  mode: OperationsMode;
  onChange: (m: OperationsMode) => void;
}) {
  return (
    <div className="inline-flex rounded-full border border-gray-300 bg-white p-1 shadow-sm">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          title={opt.hint}
          onClick={() => onChange(opt.value)}
          className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-colors ${
            mode === opt.value
              ? "bg-gray-900 text-white"
              : "text-gray-500 hover:text-gray-800"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
