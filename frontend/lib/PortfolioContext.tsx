"use client";

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import { listPortfolios, createPortfolio as apiCreate, deletePortfolio as apiDelete } from "@/lib/api";
import type { Portfolio } from "@/lib/api";

interface PortfolioContextValue {
  portfolios: Portfolio[];
  activeId: number | null;
  setActiveId: (id: number) => void;
  createPortfolio: (name: string) => Promise<Portfolio>;
  deletePortfolio: (id: number) => Promise<void>;
  refreshPortfolios: () => Promise<void>;
  loading: boolean;
}

const PortfolioContext = createContext<PortfolioContextValue | null>(null);

const STORAGE_KEY = "active_portfolio_id";

export function PortfolioProvider({ children }: { children: ReactNode }) {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [activeId, setActiveIdState] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listPortfolios()
      .then((list) => {
        setPortfolios(list);
        const saved = parseInt(localStorage.getItem(STORAGE_KEY) ?? "", 10);
        const valid = list.find((p) => p.id === saved)?.id ?? list[0]?.id ?? null;
        setActiveIdState(valid);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const setActiveId = useCallback((id: number) => {
    setActiveIdState(id);
    localStorage.setItem(STORAGE_KEY, id.toString());
  }, []);

  const createPortfolio = useCallback(async (name: string): Promise<Portfolio> => {
    const p = await apiCreate(name);
    setPortfolios((prev) => [...prev, p]);
    return p;
  }, []);

  const deletePortfolio = useCallback(async (id: number): Promise<void> => {
    await apiDelete(id);
    setPortfolios((prev) => {
      const remaining = prev.filter((p) => p.id !== id);
      if (activeId === id && remaining.length > 0) {
        setActiveId(remaining[0].id);
      }
      return remaining;
    });
  }, [activeId, setActiveId]);

  const refreshPortfolios = useCallback(async (): Promise<void> => {
    const list = await listPortfolios();
    setPortfolios(list);
  }, []);

  return (
    <PortfolioContext.Provider value={{ portfolios, activeId, setActiveId, createPortfolio, deletePortfolio, refreshPortfolios, loading }}>
      {children}
    </PortfolioContext.Provider>
  );
}

export function usePortfolio() {
  const ctx = useContext(PortfolioContext);
  if (!ctx) throw new Error("usePortfolio must be used within PortfolioProvider");
  return ctx;
}
