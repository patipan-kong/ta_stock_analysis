"use client";

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import { listPortfolios, createPortfolio as apiCreate, deletePortfolio as apiDelete } from "@/lib/api";
import type { Portfolio } from "@/lib/api";
import { resolvePortfolioReference } from "@/lib/portfolioReference";

interface PortfolioContextValue {
  portfolios: Portfolio[];
  /**
   * M36-WP1 Current Selection: zero-or-one, no architecture default. This is
   * the canonical Current Selection accessor.
   */
  currentSelection: number | null;
  /** True iff a Current Selection is presently held. Never implies availability or authority. */
  hasSelection: boolean;
  /**
   * The canonical way to explicitly change Current Selection. Validates
   * `id` against the current portfolio list via resolvePortfolioReference()
   * before persisting — an id that doesn't resolve (foreign, stale) produces
   * NONE instead of being written through (M36.1 WP4A F03).
   */
  selectPortfolio: (id: number) => void;
  /** Explicitly clears Current Selection to NONE. Never selects another portfolio. */
  clearSelection: () => void;
  /**
   * M36.1 WP4A F03 — reports that a portfolio-scoped request received an
   * authoritative "Portfolio not found" response for `id` (see
   * lib/api.ts's isUnresolvedPortfolioError). Triggers a portfolio-list
   * refresh so referenceability can be re-resolved; never selects another
   * portfolio, and only clears Current Selection if it still points at `id`
   * after the refresh (so a report about a portfolio the user has since
   * switched away from is a no-op).
   */
  reportUnresolvedPortfolio: (id: number) => void;
  createPortfolio: (name: string) => Promise<Portfolio>;
  deletePortfolio: (id: number) => Promise<void>;
  refreshPortfolios: () => Promise<void>;
  loading: boolean;
}

const PortfolioContext = createContext<PortfolioContextValue | null>(null);

const STORAGE_KEY = "workspace_current_selection";
// Pre-M36.1 key. Read once as a migration bridge, then never consulted again.
const LEGACY_STORAGE_KEY = "active_portfolio_id";

function readPersistedSelection(): number | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw !== null) {
    const parsed = parseInt(raw, 10);
    return Number.isNaN(parsed) ? null : parsed;
  }

  const legacyRaw = localStorage.getItem(LEGACY_STORAGE_KEY);
  if (legacyRaw === null) return null;

  localStorage.removeItem(LEGACY_STORAGE_KEY);
  const parsed = parseInt(legacyRaw, 10);
  if (Number.isNaN(parsed)) return null;
  localStorage.setItem(STORAGE_KEY, String(parsed));
  return parsed;
}

export function PortfolioProvider({ children }: { children: ReactNode }) {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [activeId, setActiveIdState] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listPortfolios()
      .then((list) => {
        setPortfolios(list);
        const saved = readPersistedSelection();
        const resolved = resolvePortfolioReference(list, saved);
        if (resolved === null) {
          // No architecture default: a missing, stale, or never-made selection
          // all resolve to NONE. Never auto-select the first portfolio, even
          // when exactly one exists.
          localStorage.removeItem(STORAGE_KEY);
          setActiveIdState(null);
        } else {
          setActiveIdState(resolved.id);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // M36.1 Phase 2: revalidate on every portfolios-list change, not just at
  // mount. A Current Selection that becomes stale, missing, or foreign to
  // the workspace (e.g. deleted through another tab/session, or dropped by
  // a refreshPortfolios() call) must clear to NONE — never keep pointing at
  // a reference that no longer resolves, and never fall back to another
  // portfolio (M36-WP1 foundation invariants 11, 21).
  useEffect(() => {
    if (loading) return;
    setActiveIdState((prev) => {
      if (prev === null) return prev;
      if (resolvePortfolioReference(portfolios, prev) !== null) return prev;
      localStorage.removeItem(STORAGE_KEY);
      return null;
    });
  }, [portfolios, loading]);

  // M36.1 WP4A F03 — every explicit selection transition is validated
  // against the current portfolio list before it can become persisted
  // Current Selection. A candidate that does not resolve (foreign id, stale
  // id) produces NONE instead — never persisted, never a silent no-op.
  const selectPortfolio = useCallback((id: number) => {
    const resolved = resolvePortfolioReference(portfolios, id);
    if (resolved === null) {
      localStorage.removeItem(STORAGE_KEY);
      setActiveIdState(null);
    } else {
      localStorage.setItem(STORAGE_KEY, resolved.id.toString());
      setActiveIdState(resolved.id);
    }
  }, [portfolios]);

  const clearSelection = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setActiveIdState(null);
  }, []);

  const reportUnresolvedPortfolio = useCallback((id: number) => {
    listPortfolios()
      .then((list) => {
        setPortfolios(list);
        setActiveIdState((prev) => {
          if (prev !== id) return prev;
          if (resolvePortfolioReference(list, prev) !== null) return prev;
          localStorage.removeItem(STORAGE_KEY);
          return null;
        });
      })
      .catch(() => {});
  }, []);

  const createPortfolio = useCallback(async (name: string): Promise<Portfolio> => {
    const p = await apiCreate(name);
    setPortfolios((prev) => [...prev, p]);
    return p;
  }, []);

  const deletePortfolio = useCallback(async (id: number): Promise<void> => {
    await apiDelete(id);
    setPortfolios((prev) => prev.filter((p) => p.id !== id));
    setActiveIdState((prev) => {
      if (prev !== id) return prev;
      // Selection is cleared, never carried over to another portfolio
      // (M36-WP1 foundation invariant 11: no fallback selection).
      localStorage.removeItem(STORAGE_KEY);
      return null;
    });
  }, []);

  const refreshPortfolios = useCallback(async (): Promise<void> => {
    const list = await listPortfolios();
    setPortfolios(list);
  }, []);

  return (
    <PortfolioContext.Provider
      value={{
        portfolios,
        currentSelection: activeId,
        hasSelection: activeId !== null,
        selectPortfolio,
        clearSelection,
        reportUnresolvedPortfolio,
        createPortfolio,
        deletePortfolio,
        refreshPortfolios,
        loading,
      }}
    >
      {children}
    </PortfolioContext.Provider>
  );
}

export function usePortfolio() {
  const ctx = useContext(PortfolioContext);
  if (!ctx) throw new Error("usePortfolio must be used within PortfolioProvider");
  return ctx;
}
