"use client";

import Link from "next/link";
import { logout } from "@/lib/auth";

export default function Navbar() {
  return (
    <nav className="bg-white border-b px-4 py-2.5">
      <div className="max-w-5xl mx-auto flex flex-wrap items-center gap-x-4 gap-y-2">

        {/* Brand */}
        <span className="text-sm font-bold text-gray-800 shrink-0">TA Stock Analysis</span>

        {/* Nav links */}
        <div className="flex items-center gap-4 text-sm text-gray-600 font-medium">
          <Link href="/" className="hover:text-blue-600">Dashboard</Link>
          <Link href="/portfolio" className="hover:text-blue-600">Portfolio</Link>
          <Link href="/watchlist" className="hover:text-blue-600">Watchlist</Link>
          <Link href="/optimizer" className="hover:text-blue-600">Optimizer</Link>
          <Link href="/model-cost-report" className="hover:text-blue-600">Model Cost Report</Link>
          <Link href="/settings" className="hover:text-blue-600">Settings</Link>
          <Link href="/system-guide" className="hover:text-blue-600">📚 Guide</Link>
        </div>

        {/* Logout */}
        <button
          onClick={logout}
          className="ml-auto text-sm text-gray-400 hover:text-gray-600 border rounded px-2.5 py-1 hover:bg-gray-50"
        >
          Logout
        </button>
      </div>
    </nav>
  );
}
