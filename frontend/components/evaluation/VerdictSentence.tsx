"use client";

// AI Evaluation M4 — L3-level generated plain-language claim. Renders the
// verdict_composer.py payload verbatim; this component never composes or
// alters sentence text (Single Source of Truth — Quant and MUJI share the
// same verdict payload, EXECUTION_INTELLIGENCE_UX.md D9).

import type { VerdictPayload } from "@/lib/api";

export default function VerdictSentence({ verdict, className = "" }: { verdict: VerdictPayload; className?: string }) {
  return (
    <div className={className}>
      <p className="text-sm font-medium text-gray-800 leading-relaxed">{verdict.th}</p>
      <p className="text-xs text-gray-400 mt-0.5">{verdict.en}</p>
    </div>
  );
}
