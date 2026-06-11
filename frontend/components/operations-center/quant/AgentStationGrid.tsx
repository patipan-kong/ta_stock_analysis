"use client";

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
  return (
    <div>
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-2">
        สถานีระบบ AI
      </p>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {STATIONS.map(({ key, title, icon }) => (
          <StationTile key={key} title={title} icon={icon} station={agentHealth[key]} />
        ))}
      </div>
    </div>
  );
}
