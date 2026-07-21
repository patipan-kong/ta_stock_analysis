import { describe, test, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PortfolioProvider } from "@/lib/PortfolioContext";
import WorkspaceScopeSwitcher from "@/components/WorkspaceScopeSwitcher";
import type { Portfolio } from "@/lib/api";

// M36.1 WP4B F06 — executable coverage for the shared switcher's Current
// Selection contract: explicit NONE option, A -> B switching, B -> NONE
// clearing, and no auto-select of a lone portfolio.

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

beforeEach(() => {
  localStorage.clear();
  listPortfolios.mockReset();
});

async function renderSwitcher(portfolios: Portfolio[]) {
  listPortfolios.mockResolvedValue(portfolios);
  render(
    <PortfolioProvider>
      <WorkspaceScopeSwitcher variant="list" noneLabel="No selection" />
    </PortfolioProvider>
  );
  await waitFor(() => expect(screen.getByText("No selection")).toBeInTheDocument());
}

describe("WorkspaceScopeSwitcher", () => {
  test("explicit NONE option is present and marked active by default", async () => {
    await renderSwitcher([makePortfolio(1), makePortfolio(2)]);
    const noneBtn = screen.getByText("No selection").closest("button")!;
    expect(noneBtn).toHaveClass("bg-blue-50");
  });

  test("a single portfolio is not auto-selected", async () => {
    await renderSwitcher([makePortfolio(1, "Solo")]);
    const noneBtn = screen.getByText("No selection").closest("button")!;
    expect(noneBtn).toHaveClass("bg-blue-50"); // NONE still active, not "Solo"
  });

  test("selecting A changes Current Selection", async () => {
    const user = userEvent.setup();
    await renderSwitcher([makePortfolio(1, "Alpha"), makePortfolio(2, "Beta")]);

    await user.click(screen.getByText("Alpha"));

    await waitFor(() => {
      expect(screen.getByText("Alpha").closest("button")).toHaveClass("bg-blue-50");
    });
    expect(localStorage.getItem("workspace_current_selection")).toBe("1");
  });

  test("switching A -> B changes Current Selection", async () => {
    const user = userEvent.setup();
    await renderSwitcher([makePortfolio(1, "Alpha"), makePortfolio(2, "Beta")]);

    await user.click(screen.getByText("Alpha"));
    await waitFor(() => expect(localStorage.getItem("workspace_current_selection")).toBe("1"));

    await user.click(screen.getByText("Beta"));
    await waitFor(() => expect(localStorage.getItem("workspace_current_selection")).toBe("2"));
    expect(screen.getByText("Beta").closest("button")).toHaveClass("bg-blue-50");
    expect(screen.getByText("Alpha").closest("button")).not.toHaveClass("bg-blue-50");
  });

  test("clearing B -> NONE works and is not persisted", async () => {
    const user = userEvent.setup();
    await renderSwitcher([makePortfolio(1, "Alpha")]);

    await user.click(screen.getByText("Alpha"));
    await waitFor(() => expect(localStorage.getItem("workspace_current_selection")).toBe("1"));

    await user.click(screen.getByText("No selection"));
    await waitFor(() => expect(localStorage.getItem("workspace_current_selection")).toBeNull());
    expect(screen.getByText("No selection").closest("button")).toHaveClass("bg-blue-50");
  });
});
