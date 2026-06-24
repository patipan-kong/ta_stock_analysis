"use client";

import { useState } from "react";
import type { AgentHealth, OperationsStation, StationStatus } from "@/lib/api";

const STATIONS: { key: keyof AgentHealth; title: string; icon: string }[] = [
  { key: "market_data_station", title: "สถานีข้อมูลตลาด",       icon: "📡" },
  { key: "macro_station",       title: "สถานีภาวะตลาด",          icon: "🌐" },
  { key: "risk_desk",           title: "ศูนย์บริหารความเสี่ยง",  icon: "🛡️" },
  { key: "quant_corner",        title: "มุมวิเคราะห์เชิงปริมาณ", icon: "📐" },
  { key: "portfolio_lab",       title: "ห้องทดลองพอร์ต",         icon: "🧪" },
  { key: "consensus_room",      title: "ห้องประชุม AI",          icon: "🤝" },
];

const LAMP: Record<StationStatus, string> = {
  GREEN:  "bg-emerald-500",
  YELLOW: "bg-amber-400",
  RED:    "bg-red-500 animate-pulse",
};

const STATUS_TEXT: Record<StationStatus, string> = {
  GREEN:  "text-emerald-600",
  YELLOW: "text-amber-600",
  RED:    "text-red-600",
};

const STATUS_LABEL_TH: Record<StationStatus, string> = {
  GREEN:  "ปกติ",
  YELLOW: "ควรดู",
  RED:    "แจ้งเตือน",
};

function StationTile({ title, icon, station }: { title: string; icon: string; station: OperationsStation }) {
  return (
    <div
      className="border-2 border-gray-900 bg-white p-4 shadow-[4px_4px_0px_#111] space-y-2"
      title={station.detail}
    >
      <div className="flex items-center justify-between">
        <span className="text-lg leading-none">{icon}</span>
        <span className={`inline-block h-3 w-3 ${LAMP[station.status]}`} />
      </div>
      <p className="font-mono text-[11px] font-bold text-gray-900 tracking-wide">{title}</p>
      <p className={`font-mono text-[10px] font-bold ${STATUS_TEXT[station.status]}`}>
        {STATUS_LABEL_TH[station.status]}
      </p>
      <p className="text-[11px] text-gray-500 leading-snug">{station.detail_th || station.detail}</p>
    </div>
  );
}

export default function AgentStationGrid({ agentHealth }: { agentHealth: AgentHealth }) {
  const [open, setOpen] = useState(false);

  const stations = STATIONS.map(({ key }) => agentHealth[key]);
  const green  = stations.filter((s) => s.status === "GREEN").length;
  const yellow = stations.filter((s) => s.status === "YELLOW").length;
  const red    = stations.filter((s) => s.status === "RED").length;
  const overall: StationStatus = red > 0 ? "RED" : yellow > 0 ? "YELLOW" : "GREEN";

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <button
        className="w-full flex items-center justify-between gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
        onClick={() => setOpen((v) => !v)}
      >
        <div className="flex items-center gap-3 flex-wrap">
          <span className={`inline-block h-2.5 w-2.5 rounded-full shrink-0 ${LAMP[overall]}`} />
          <span className="text-sm font-medium text-gray-800">System Health</span>
          <div className="flex items-center gap-3 text-xs text-gray-500">
            {green  > 0 && <span>🟢 {green} Healthy</span>}
            {yellow > 0 && <span>🟡 {yellow} Warning</span>}
            {red    > 0 && <span>🔴 {red} Alert</span>}
          </div>
        </div>
        <span className="text-xs text-gray-400 shrink-0">{open ? "Hide" : "Show Details"}</span>
      </button>

      {open && (
        <div className="px-4 pb-4">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {STATIONS.map(({ key, title, icon }) => (
              <StationTile key={key} title={title} icon={icon} station={agentHealth[key]} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
