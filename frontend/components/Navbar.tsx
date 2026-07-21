"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { logout } from "@/lib/auth";
import { usePortfolio } from "@/lib/PortfolioContext";
import { getSystemStatus, type SystemStatus } from "@/lib/api";
import WorkspaceScopeSwitcher from "@/components/WorkspaceScopeSwitcher";

// Phase 4C.2A — Soft consolidation: 4 top-level destinations.
// `match` lists every route prefix that belongs to this hub, so the nav item
// stays highlighted while browsing sub-pages (e.g. /performance lives under
// the Portfolio hub). All legacy routes (/, /optimizer, /portfolio-intelligence,
// /performance, /analytics) remain fully functional — only nav exposure changed.
const NAV_MAIN: { label: string; href: string; match: string[] }[] = [
  {
    label: "พอร์ตโฟลิโอ",
    href: "/portfolio",
    match: ["/portfolio", "/performance", "/analytics", "/stock"],
  },
  { label: "รายการเฝ้าดู", href: "/watchlist", match: ["/watchlist"] },
  {
    label: "ศูนย์บัญชาการ AI",
    href: "/operations-center",
    match: ["/operations-center", "/optimizer", "/portfolio-intelligence"],
  },
  // AI Evaluation Hub (Scorecard / Recommendations / Execution / Human vs AI /
  // Opportunity Cost) — promoted from the ⚙ ระบบ dropdown to primary nav so
  // it's discoverable, not tucked next to Settings. Prefix match also covers
  // /ai-analytics/system (AI ops telemetry), still one click away per its own
  // header link (docs/AI_EVALUATION_IMPLEMENTATION_PLAN.md Planning Decision P1).
  { label: "ประเมินผล AI", href: "/ai-analytics", match: ["/ai-analytics"] },
  { label: "📚 คู่มือ", href: "/system-guide", match: ["/system-guide"] },
];

const NAV_ADMIN = [
  { label: "ตั้งค่า", href: "/settings" },
];

function isActive(match: string[], pathname: string) {
  return match.some((prefix) =>
    prefix === "/" ? pathname === "/" : pathname.startsWith(prefix)
  );
}

export default function Navbar() {
  const pathname = usePathname();
  const { portfolios } = usePortfolio();
  const [adminOpen, setAdminOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sysStatus, setSysStatus] = useState<SystemStatus | null>(null);
  const adminRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getSystemStatus()
      .then(setSysStatus)
      .catch(() => {});
  }, []);

  // Close dropdowns on outside click
  useEffect(() => {
    function onMouseDown(e: MouseEvent) {
      if (adminRef.current && !adminRef.current.contains(e.target as Node)) {
        setAdminOpen(false);
      }
    }
    document.addEventListener("mousedown", onMouseDown);
    return () => document.removeEventListener("mousedown", onMouseDown);
  }, []);

  // Close everything on route change
  useEffect(() => {
    setAdminOpen(false);
    setMobileOpen(false);
  }, [pathname]);

  const adminActive = NAV_ADMIN.some((n) => isActive([n.href], pathname));

  return (
    <nav className="bg-white border-b px-4 py-2.5">
      {/* ── Desktop row ── */}
      <div className="max-w-5xl mx-auto flex items-center gap-2">

        {/* Brand — links to the legacy dashboard (route kept; removed from nav) */}
        <Link
          href="/"
          className="text-sm font-bold text-gray-800 shrink-0 mr-4 hover:text-blue-700 transition-colors"
        >
          📈 Portfolio Intelligence
        </Link>

        {/* Cloud Dashboard Mode badge — shown only when APP_ENV=vps */}
        {sysStatus?.read_only_market_data && (
          <span
            title="Market data synced from Local Research Node. Live fetching disabled."
            className="hidden md:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-sky-50 text-sky-700 border border-sky-200 shrink-0 mr-1"
          >
            ☁ Cloud Dashboard
          </span>
        )}

        {/* Main nav — flat links */}
        <div className="hidden md:flex items-center gap-1">
          {NAV_MAIN.map(({ label, href, match }) => (
            <Link
              key={href}
              href={href}
              className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                isActive(match, pathname)
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-800"
              }`}
            >
              {label}
            </Link>
          ))}
        </div>

        {/* Push admin + logout to the right */}
        <div className="hidden md:flex items-center gap-2 ml-auto">

          {/* Portfolio selector — M36.1 Phase 3 shared Workspace-Scope contract */}
          <WorkspaceScopeSwitcher variant="dropdown" label="เลือกพอร์ต" noneLabel="ไม่ได้เลือกพอร์ต" />

          {/* Admin dropdown */}
          <div className="relative" ref={adminRef}>
            <button
              onClick={() => setAdminOpen((o) => !o)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                adminActive
                  ? "bg-gray-100 text-gray-800"
                  : "text-gray-500 hover:bg-gray-100 hover:text-gray-700"
              }`}
            >
              <span>⚙</span>
              <span>ระบบ</span>
              <span className="text-xs text-gray-400">{adminOpen ? "▲" : "▼"}</span>
            </button>

            {adminOpen && (
              <div className="absolute right-0 mt-1.5 w-48 bg-white border border-gray-200 rounded-xl shadow-lg py-1.5 z-50">
                {NAV_ADMIN.map(({ label, href }) => (
                  <Link
                    key={href}
                    href={href}
                    className={`flex items-center px-4 py-2 text-sm transition-colors ${
                      isActive([href], pathname)
                        ? "bg-blue-50 text-blue-700 font-medium"
                        : "text-gray-700 hover:bg-gray-50"
                    }`}
                  >
                    {label}
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Logout */}
          <button
            onClick={logout}
            className="text-sm text-gray-400 hover:text-gray-600 border rounded px-2.5 py-1 hover:bg-gray-50"
          >
            ออกจากระบบ
          </button>
        </div>

        {/* Hamburger — mobile only */}
        <button
          onClick={() => setMobileOpen((o) => !o)}
          className="md:hidden ml-auto p-1.5 rounded-md text-gray-500 hover:bg-gray-100 text-base leading-none"
          aria-label="Toggle menu"
        >
          {mobileOpen ? "✕" : "☰"}
        </button>
      </div>

      {/* ── Mobile panel ── */}
      {mobileOpen && (
        <div className="md:hidden mt-2 border-t pt-3 pb-2 space-y-0.5">
          <p className="px-3 pb-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">เมนูหลัก</p>
          {NAV_MAIN.map(({ label, href, match }) => (
            <Link
              key={href}
              href={href}
              className={`block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive(match, pathname)
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
            >
              {label}
            </Link>
          ))}

          {portfolios.length > 0 && (
            <>
              <div className="my-2 border-t" />
              <p className="px-3 pb-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">เลือกพอร์ต</p>
              <WorkspaceScopeSwitcher variant="list" noneLabel="ไม่ได้เลือกพอร์ต" className="space-y-0.5" />
            </>
          )}

          <div className="my-2 border-t" />

          <p className="px-3 pb-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">ระบบ</p>
          {NAV_ADMIN.map(({ label, href }) => (
            <Link
              key={href}
              href={href}
              className={`block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive([href], pathname)
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              {label}
            </Link>
          ))}

          <div className="my-2 border-t" />

          <button
            onClick={logout}
            className="w-full text-left px-3 py-2 rounded-md text-sm text-gray-400 hover:text-gray-600 hover:bg-gray-50"
          >
            ออกจากระบบ
          </button>
        </div>
      )}
    </nav>
  );
}
