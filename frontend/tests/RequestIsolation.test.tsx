import { describe, test, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import { PortfolioProvider, usePortfolio } from "@/lib/PortfolioContext";
import HumanVsAiPage from "@/app/ai-analytics/(hub)/human-vs-ai/page";
import type { Portfolio } from "@/lib/api";

// M36.1 WP4B F06 — request/state isolation coverage using a real F04
// consumer (human-vs-ai/page.tsx) rather than a synthetic harness, so the
// test exercises the actual requestIdRef guard shipped in the page: NONE
// suppresses the portfolio-scoped request, a delayed A response after
// switching to B (or clearing to NONE) is ignored, and a valid B response
// is accepted.

const { listPortfolios, createPortfolio, deletePortfolio, getHumanVsAiScoreboard, isUnresolvedPortfolioError } =
  vi.hoisted(() => ({
    listPortfolios: vi.fn(),
    createPortfolio: vi.fn(),
    deletePortfolio: vi.fn(),
    getHumanVsAiScoreboard: vi.fn(),
    isUnresolvedPortfolioError: vi.fn(() => false),
  }));

vi.mock("@/lib/api", () => ({
  listPortfolios,
  createPortfolio,
  deletePortfolio,
  getHumanVsAiScoreboard,
  isUnresolvedPortfolioError,
}));

function makePortfolio(id: number, name = `P${id}`): Portfolio {
  return { id, name, cash_balance: 0, created_at: "2026-01-01T00:00:00Z" };
}

// A and B render distinguishable summary numbers (not just a different
// __tag, which nothing on the page displays) so a race-condition test can
// prove which portfolio's data actually rendered, not merely that nothing
// crashed.
function scoreboard(tag: "A" | "B") {
  const summary =
    tag === "A"
      ? { n_graded: 6, you_beat_ai: 5, ai_beat_you: 1, ties: 0, maturing: 0, net_effect_pct: 4 }
      : { n_graded: 6, you_beat_ai: 1, ai_beat_you: 5, ties: 0, maturing: 0, net_effect_pct: -4 };
  return {
    status: "ok",
    as_of: "2026-01-01",
    tie_band_pct: 1,
    summary,
    by_trade_class: {},
    by_override_type: {},
    __tag: tag,
  } as any;
}

// A deferred promise so the test controls exactly when each fetch resolves.
function deferred<T>() {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((r) => (resolve = r));
  return { promise, resolve };
}

function SwitcherProbe() {
  const { selectPortfolio, clearSelection } = usePortfolio();
  return (
    <div>
      <button onClick={() => selectPortfolio(1)}>select-A</button>
      <button onClick={() => selectPortfolio(2)}>select-B</button>
      <button onClick={() => clearSelection()}>clear</button>
    </div>
  );
}

beforeEach(() => {
  localStorage.clear();
  listPortfolios.mockReset();
  getHumanVsAiScoreboard.mockReset();
});

test("NONE issues no portfolio-scoped request", async () => {
  listPortfolios.mockResolvedValue([makePortfolio(1), makePortfolio(2)]);
  render(
    <PortfolioProvider>
      <SwitcherProbe />
      <HumanVsAiPage />
    </PortfolioProvider>
  );
  await waitFor(() => expect(screen.getByText(/Select a portfolio/)).toBeInTheDocument());
  expect(getHumanVsAiScoreboard).not.toHaveBeenCalled();
});

test("A -> B: B resolves first and renders, a late A response arriving afterwards must not overwrite it", async () => {
  listPortfolios.mockResolvedValue([makePortfolio(1), makePortfolio(2)]);
  const a = deferred<any>();
  const b = deferred<any>();
  getHumanVsAiScoreboard.mockImplementation((pid: number) => (pid === 1 ? a.promise : b.promise));

  render(
    <PortfolioProvider>
      <SwitcherProbe />
      <HumanVsAiPage />
    </PortfolioProvider>
  );
  await waitFor(() => expect(screen.getByText(/Select a portfolio/)).toBeInTheDocument());

  await act(async () => screen.getByText("select-A").click());
  await waitFor(() => expect(getHumanVsAiScoreboard).toHaveBeenCalledWith(1, 90));

  // Switch to B while A's request is still in flight.
  await act(async () => screen.getByText("select-B").click());
  await waitFor(() => expect(getHumanVsAiScoreboard).toHaveBeenCalledWith(2, 90));

  // B resolves first (the realistic ordering: A was issued earlier but is
  // slower — e.g. a heavier query — while B, issued later, returns first).
  // B's fixture ("The AI came out ahead...") is the opposite verdict from
  // A's fixture ("You came out ahead...") so the assertion below proves
  // which portfolio's data actually rendered, not just that nothing crashed.
  await act(async () => b.resolve(scoreboard("B")));
  await waitFor(() => expect(screen.getByText(/The AI came out ahead/)).toBeInTheDocument());

  // A's stale response for the now-abandoned portfolio lands after B has
  // already rendered — the requestIdRef guard (currentSelection === 2, A
  // was captured for pid 1) must discard it, not overwrite B's data.
  await act(async () => a.resolve(scoreboard("A")));

  expect(screen.getByText(/The AI came out ahead/)).toBeInTheDocument();
  expect(screen.queryByText(/You came out ahead/)).not.toBeInTheDocument();
  expect(getHumanVsAiScoreboard).toHaveBeenCalledTimes(2);
});

test("A -> NONE: a delayed A response is ignored and the page returns to the selection boundary", async () => {
  listPortfolios.mockResolvedValue([makePortfolio(1), makePortfolio(2)]);
  const a = deferred<any>();
  getHumanVsAiScoreboard.mockImplementation(() => a.promise);

  render(
    <PortfolioProvider>
      <SwitcherProbe />
      <HumanVsAiPage />
    </PortfolioProvider>
  );
  await waitFor(() => expect(screen.getByText(/Select a portfolio/)).toBeInTheDocument());

  await act(async () => screen.getByText("select-A").click());
  await waitFor(() => expect(getHumanVsAiScoreboard).toHaveBeenCalledWith(1, 90));

  await act(async () => screen.getByText("clear").click());
  expect(screen.getByText(/Select a portfolio/)).toBeInTheDocument();

  // A's stale response lands after clearing to NONE — must not repopulate the page.
  await act(async () => a.resolve(scoreboard("A")));
  expect(screen.getByText(/Select a portfolio/)).toBeInTheDocument();
});
