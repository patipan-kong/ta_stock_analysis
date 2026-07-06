"use client";

import ComingSoonScreen from "@/components/evaluation/ComingSoonScreen";

export default function HumanVsAiPlaceholderPage() {
  return (
    <ComingSoonScreen
      title="Human vs AI"
      milestone="M5"
      description="Cumulative scoreboard of your decisions vs full AI compliance, segmented by trade class and override type — plus the Opportunity Cost counterfactual ledger, reached from within this tab."
    />
  );
}
