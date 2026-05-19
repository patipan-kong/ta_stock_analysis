"use client";

import { useState } from "react";
import Link from "next/link";
import { usePortfolio } from "@/lib/PortfolioContext";
import { logout } from "@/lib/auth";

export default function Navbar() {
  const { portfolios, activeId, setActiveId, createPortfolio, deletePortfolio } = usePortfolio();
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return;
    const p = await createPortfolio(name);
    setActiveId(p.id);
    setNewName("");
    setCreating(false);
  }

  async function handleDelete() {
    if (activeId == null) return;
    await deletePortfolio(activeId);
    setConfirmDelete(false);
  }

  const activePortfolio = portfolios.find((p) => p.id === activeId);

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

        {/* Portfolio selector — pushed right */}
        <div className="ml-auto flex items-center gap-2 flex-wrap">
          {creating ? (
            <form onSubmit={handleCreate} className="flex items-center gap-1">
              <input
                autoFocus
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Portfolio name"
                className="text-sm border rounded px-2 py-1 w-36"
              />
              <button type="submit" className="text-xs bg-blue-600 text-white px-2.5 py-1 rounded hover:bg-blue-700">
                Save
              </button>
              <button
                type="button"
                onClick={() => { setCreating(false); setNewName(""); }}
                className="text-xs text-gray-400 hover:text-gray-600 px-1"
              >
                ✕
              </button>
            </form>
          ) : confirmDelete ? (
            <div className="flex items-center gap-2 text-sm">
              <span className="text-gray-500">Delete "{activePortfolio?.name}"?</span>
              <button onClick={handleDelete} className="text-xs bg-red-600 text-white px-2.5 py-1 rounded hover:bg-red-700">
                Yes
              </button>
              <button onClick={() => setConfirmDelete(false)} className="text-xs text-gray-400 hover:text-gray-600">
                Cancel
              </button>
            </div>
          ) : (
            <>
              {portfolios.length > 0 && (
                <select
                  value={activeId ?? ""}
                  onChange={(e) => setActiveId(parseInt(e.target.value, 10))}
                  className="text-sm border rounded px-2 py-1 bg-white max-w-[140px]"
                >
                  {portfolios.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              )}
              <button
                onClick={() => setCreating(true)}
                title="New portfolio"
                className="text-sm border rounded px-2.5 py-1 hover:bg-gray-50 text-gray-600"
              >
                + New
              </button>
              {portfolios.length > 1 && (
                <button
                  onClick={() => setConfirmDelete(true)}
                  title="Delete this portfolio"
                  className="text-sm border border-red-200 rounded px-2.5 py-1 hover:bg-red-50 text-red-400"
                >
                  Delete
                </button>
              )}
              <button
                onClick={logout}
                className="text-sm text-gray-400 hover:text-gray-600 border rounded px-2.5 py-1 hover:bg-gray-50"
              >
                Logout
              </button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
