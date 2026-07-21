import { describe, test, expect, vi, beforeEach } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { PortfolioProvider, usePortfolio } from "@/lib/PortfolioContext";
import type { Portfolio } from "@/lib/api";

// M36.1 WP4B F06 — executable coverage for PortfolioContext's Current
// Selection transitions (M36-WP1 §9: zero-or-one, no architecture default,
// no fallback). lib/api.ts is mocked so these tests exercise only
// PortfolioContext's own resolution/validation logic, not network behavior.

const { listPortfolios, createPortfolio, deletePortfolio } = vi.hoisted(() => ({
  listPortfolios: vi.fn(),
  createPortfolio: vi.fn(),
  deletePortfolio: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  listPortfolios,
  createPortfolio,
  deletePortfolio,
}));

function makePortfolio(id: number, name = `P${id}`): Portfolio {
  return { id, name, cash_balance: 0, created_at: "2026-01-01T00:00:00Z" };
}

const STORAGE_KEY = "workspace_current_selection";

beforeEach(() => {
  localStorage.clear();
  listPortfolios.mockReset();
  createPortfolio.mockReset();
  deletePortfolio.mockReset();
});

async function renderPortfolio(initialList: Portfolio[]) {
  listPortfolios.mockResolvedValue(initialList);
  const view = renderHook(() => usePortfolio(), { wrapper: PortfolioProvider });
  await waitFor(() => expect(view.result.current.loading).toBe(false));
  return view;
}

describe("PortfolioContext hydration", () => {
  test("zero portfolios -> NONE", async () => {
    const { result } = await renderPortfolio([]);
    expect(result.current.currentSelection).toBeNull();
    expect(result.current.hasSelection).toBe(false);
  });

  test("one portfolio, no saved selection -> NONE (no auto-select)", async () => {
    const { result } = await renderPortfolio([makePortfolio(1)]);
    expect(result.current.currentSelection).toBeNull();
  });

  test("many portfolios, no saved selection -> NONE", async () => {
    const { result } = await renderPortfolio([makePortfolio(1), makePortfolio(2), makePortfolio(3)]);
    expect(result.current.currentSelection).toBeNull();
  });

  test("valid persisted selection survives exact validation", async () => {
    localStorage.setItem(STORAGE_KEY, "2");
    const { result } = await renderPortfolio([makePortfolio(1), makePortfolio(2)]);
    expect(result.current.currentSelection).toBe(2);
  });

  test("stale persisted selection clears to NONE and is removed from storage", async () => {
    localStorage.setItem(STORAGE_KEY, "999");
    const { result } = await renderPortfolio([makePortfolio(1), makePortfolio(2)]);
    expect(result.current.currentSelection).toBeNull();
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });
});

describe("PortfolioContext explicit selection transitions", () => {
  test("selectPortfolio with a valid id persists and updates", async () => {
    const { result } = await renderPortfolio([makePortfolio(1), makePortfolio(2)]);
    act(() => result.current.selectPortfolio(2));
    expect(result.current.currentSelection).toBe(2);
    expect(localStorage.getItem(STORAGE_KEY)).toBe("2");
  });

  test("selectPortfolio with an unresolved (foreign/stale) id resolves to NONE, not persisted", async () => {
    const { result } = await renderPortfolio([makePortfolio(1)]);
    act(() => result.current.selectPortfolio(1));
    expect(result.current.currentSelection).toBe(1);

    act(() => result.current.selectPortfolio(777));
    expect(result.current.currentSelection).toBeNull();
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  test("clearSelection -> NONE with no fallback", async () => {
    const { result } = await renderPortfolio([makePortfolio(1)]);
    act(() => result.current.selectPortfolio(1));
    expect(result.current.currentSelection).toBe(1);

    act(() => result.current.clearSelection());
    expect(result.current.currentSelection).toBeNull();
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });
});

describe("PortfolioContext list-change revalidation", () => {
  test("selected portfolio removed from refreshed list -> NONE", async () => {
    listPortfolios.mockResolvedValueOnce([makePortfolio(1), makePortfolio(2)]);
    const { result } = renderHook(() => usePortfolio(), { wrapper: PortfolioProvider });
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => result.current.selectPortfolio(2));
    expect(result.current.currentSelection).toBe(2);

    listPortfolios.mockResolvedValueOnce([makePortfolio(1)]);
    await act(async () => {
      await result.current.refreshPortfolios();
    });

    expect(result.current.currentSelection).toBeNull();
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  test("deleting a different portfolio preserves current selection", async () => {
    const { result } = await renderPortfolio([makePortfolio(1), makePortfolio(2)]);
    act(() => result.current.selectPortfolio(1));
    expect(result.current.currentSelection).toBe(1);

    deletePortfolio.mockResolvedValueOnce(undefined);
    await act(async () => {
      await result.current.deletePortfolio(2);
    });

    expect(result.current.currentSelection).toBe(1);
  });

  test("deleting the selected portfolio clears to NONE with no fallback", async () => {
    const { result } = await renderPortfolio([makePortfolio(1), makePortfolio(2)]);
    act(() => result.current.selectPortfolio(1));

    deletePortfolio.mockResolvedValueOnce(undefined);
    await act(async () => {
      await result.current.deletePortfolio(1);
    });

    expect(result.current.currentSelection).toBeNull();
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });
});

describe("PortfolioContext creation does not change selection (F02)", () => {
  test("create while NONE remains NONE", async () => {
    const { result } = await renderPortfolio([makePortfolio(1)]);
    expect(result.current.currentSelection).toBeNull();

    createPortfolio.mockResolvedValueOnce(makePortfolio(2, "New"));
    await act(async () => {
      await result.current.createPortfolio("New");
    });

    expect(result.current.currentSelection).toBeNull();
    expect(result.current.portfolios.map((p) => p.id)).toEqual([1, 2]);
  });

  test("create while A selected preserves A", async () => {
    const { result } = await renderPortfolio([makePortfolio(1)]);
    act(() => result.current.selectPortfolio(1));
    expect(result.current.currentSelection).toBe(1);

    createPortfolio.mockResolvedValueOnce(makePortfolio(2, "New"));
    await act(async () => {
      await result.current.createPortfolio("New");
    });

    expect(result.current.currentSelection).toBe(1);
  });
});

describe("PortfolioContext F03 unresolved-response recovery", () => {
  test("reportUnresolvedPortfolio clears selection only if it still matches after refresh", async () => {
    listPortfolios.mockResolvedValueOnce([makePortfolio(1), makePortfolio(2)]);
    const { result } = renderHook(() => usePortfolio(), { wrapper: PortfolioProvider });
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => result.current.selectPortfolio(1));

    listPortfolios.mockResolvedValueOnce([makePortfolio(2)]); // 1 no longer exists
    await act(async () => {
      result.current.reportUnresolvedPortfolio(1);
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(result.current.currentSelection).toBeNull();
  });

  test("reportUnresolvedPortfolio is a no-op if the user already switched away", async () => {
    listPortfolios.mockResolvedValueOnce([makePortfolio(1), makePortfolio(2)]);
    const { result } = renderHook(() => usePortfolio(), { wrapper: PortfolioProvider });
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => result.current.selectPortfolio(1));
    act(() => result.current.selectPortfolio(2)); // user switched to 2 before the stale report for 1 arrives

    listPortfolios.mockResolvedValueOnce([makePortfolio(2)]);
    await act(async () => {
      result.current.reportUnresolvedPortfolio(1); // stale report about 1, not the current selection
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(result.current.currentSelection).toBe(2);
  });
});
