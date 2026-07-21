// Pure-function tests for resolvePortfolioReference() (M36.1 Phase 2).
//
// No test framework is configured in this repo (no Jest/Vitest). Per the
// M36.1 Phase 2 brief, the smallest safe mechanism already available is
// Node's built-in test runner + experimental TypeScript type-stripping
// (Node >=22.6), which needs no new dependency. Run with:
//
//   node --experimental-strip-types --test lib/portfolioReference.test.ts
//
// This is a stopgap, not a replacement for a real frontend test harness —
// see docs/implementation/M36_1_Runtime_Foundation.md's testing strategy
// section for the still-missing Jest/Vitest setup, recorded as technical
// debt rather than silent coverage.
import assert from "node:assert/strict";
import { test } from "node:test";

import { resolvePortfolioReference } from "./portfolioReference.ts";
import type { Portfolio } from "./api.ts";

function portfolio(id: number, name = `P${id}`): Portfolio {
  return { id, name, cash_balance: 0, created_at: "2026-01-01T00:00:00Z" };
}

test("resolves an id that exists in the list", () => {
  const list = [portfolio(1), portfolio(2)];
  const result = resolvePortfolioReference(list, 2);
  assert.equal(result?.id, 2);
});

test("returns null for an id not present in the list (stale/foreign reference)", () => {
  const list = [portfolio(1), portfolio(2)];
  assert.equal(resolvePortfolioReference(list, 99), null);
});

test("returns null when id is null (no Current Selection) without inspecting the list", () => {
  assert.equal(resolvePortfolioReference([portfolio(1)], null), null);
});

test("returns null against an empty list, for any id", () => {
  assert.equal(resolvePortfolioReference([], 1), null);
});

test("never falls back to the first portfolio when the requested id is absent", () => {
  const list = [portfolio(5), portfolio(6), portfolio(7)];
  const result = resolvePortfolioReference(list, 42);
  assert.equal(result, null);
  assert.notEqual(result?.id, list[0].id);
});

test("is independent of list order (identity match, not position)", () => {
  const list = [portfolio(3), portfolio(1), portfolio(2)];
  assert.equal(resolvePortfolioReference(list, 1)?.id, 1);
});
