"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { logout } from "@/lib/auth";
import { usePortfolio } from "@/lib/PortfolioContext";
import { getSystemStatus, type SystemStatus } from "@/lib/api";

const NAV_MAIN = [
  { label: "Dashboard",   href: "/" },
  { label: "Portfolio",   href: "/portfolio" },
  { label: "Performance", href: "/performance" },
  { label: "Analytics",   href: "/analytics" },
  { label: "Portfolio Intelligence", href: "/portfolio-intelligence" },
  { label: "Watchlist",   href: "/watchlist" },
  { label: "Optimizer",   href: "/optimizer" },
  { label: "📚 Guide",    href: "/system-guide" },
];

const NAV_ADMIN = [
  { label: "Settings",    href: "/settings" },
  { label: "Stats",       href: "/stats" },
  { label: "Cost Report", href: "/model-cost-report" },
];

function isActive(href: string, pathname: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export default function Navbar() {
  const pathname = usePathname();
  const { portfolios, activeId, setActiveId } = usePortfolio();
  const [adminOpen, setAdminOpen] = useState(false);
  const [portfolioOpen, setPortfolioOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sysStatus, setSysStatus] = useState<SystemStatus | null>(null);
  const adminRef = useRef<HTMLDivElement>(null);
  const portfolioRef = useRef<HTMLDivElement>(null);

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
      if (portfolioRef.current && !portfolioRef.current.contains(e.target as Node)) {
        setPortfolioOpen(false);
      }
    }
    document.addEventListener("mousedown", onMouseDown);
    return () => document.removeEventListener("mousedown", onMouseDown);
  }, []);

  // Close everything on route change
  useEffect(() => {
    setAdminOpen(false);
    setPortfolioOpen(false);
    setMobileOpen(false);
  }, [pathname]);

  const activePortfolioName = portfolios.find((p) => p.id === activeId)?.name ?? "Portfolio";

  const adminActive = NAV_ADMIN.some((n) => isActive(n.href, pathname));

  return (
    <nav className="bg-white border-b px-4 py-2.5">
      {/* ── Desktop row ── */}
      <div className="max-w-5xl mx-auto flex items-center gap-1">

        {/* Brand */}
        <span className="text-sm font-bold text-gray-800 shrink-0 mr-3">📈 Portfolio Intelligence</span>

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
        <div className="hidden md:flex items-center gap-0.5">
          {NAV_MAIN.map(({ label, href }) => (
            <Link
              key={href}
              href={href}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                isActive(href, pathname)
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

          {/* Portfolio selector */}
          {portfolios.length > 0 && (
            <div className="relative" ref={portfolioRef}>
              <button
                onClick={() => setPortfolioOpen((o) => !o)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-800 transition-colors max-w-[160px]"
              >
                <span className="truncate">{activePortfolioName}</span>
                <span className={`text-xs text-gray-400 shrink-0 transition-transform ${portfolioOpen ? "rotate-180" : ""}`}>▼</span>
              </button>
              {portfolioOpen && (
                <div className="absolute right-0 mt-1.5 w-48 bg-white border border-gray-200 rounded-xl shadow-lg py-1.5 z-50">
                  <p className="px-4 pb-1 pt-0.5 text-xs font-semibold text-gray-400 uppercase tracking-wider">Switch Portfolio</p>
                  {portfolios.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => { setActiveId(p.id); setPortfolioOpen(false); }}
                      className={`flex items-center w-full px-4 py-2 text-sm transition-colors ${
                        p.id === activeId
                          ? "bg-blue-50 text-blue-700 font-medium"
                          : "text-gray-700 hover:bg-gray-50"
                      }`}
                    >
                      {p.id === activeId && <span className="mr-2 text-blue-500">✓</span>}
                      <span className="truncate">{p.name}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

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
              <span>Admin</span>
              <span className={`text-xs text-gray-400 transition-transform ${adminOpen ? "rotate-180" : ""}`}>▼</span>
            </button>

            {adminOpen && (
              <div className="absolute right-0 mt-1.5 w-44 bg-white border border-gray-200 rounded-xl shadow-lg py-1.5 z-50">
                {NAV_ADMIN.map(({ label, href }) => (
                  <Link
                    key={href}
                    href={href}
                    className={`flex items-center px-4 py-2 text-sm transition-colors ${
                      isActive(href, pathname)
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
            Logout
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
          <p className="px-3 pb-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">Menu</p>
          {NAV_MAIN.map(({ label, href }) => (
            <Link
              key={href}
              href={href}
              className={`block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive(href, pathname)
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
              <p className="px-3 pb-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">Portfolio</p>
              {portfolios.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setActiveId(p.id)}
                  className={`flex items-center w-full px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    p.id === activeId
                      ? "bg-blue-50 text-blue-700"
                      : "text-gray-700 hover:bg-gray-100"
                  }`}
                >
                  {p.id === activeId && <span className="mr-2 text-blue-500">✓</span>}
                  {p.name}
                </button>
              ))}
            </>
          )}

          <div className="my-2 border-t" />

          <p className="px-3 pb-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">Admin</p>
          {NAV_ADMIN.map(({ label, href }) => (
            <Link
              key={href}
              href={href}
              className={`block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive(href, pathname)
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
            Logout
          </button>
        </div>
      )}
    </nav>
  );
}
