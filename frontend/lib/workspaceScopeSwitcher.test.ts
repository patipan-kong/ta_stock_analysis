// Pure-function tests for resolveActiveLabel() (M36.1 Phase 3).
//
// Same rationale/mechanism as portfolioReference.test.ts — no Jest/Vitest in
// this repo; Node's built-in test runner + --experimental-strip-types.
//
//   node --experimental-strip-types --test lib/workspaceScopeSwitcher.test.ts
import assert from "node:assert/strict";
import { test } from "node:test";

import { resolveActiveLabel } from "./workspaceScopeSwitcher.ts";

function portfolio(id: number, name = `P${id}`) {
  return { id, name };
}

test("resolves the label of the selected portfolio by exact id match", () => {
  const list = [portfolio(1, "Alpha"), portfolio(2, "Beta")];
  assert.equal(resolveActiveLabel(list, 2, "None"), "Beta");
});

test("returns noneLabel when activeId is null", () => {
  const list = [portfolio(1, "Alpha")];
  assert.equal(resolveActiveLabel(list, null, "None selected"), "None selected");
});

test("returns noneLabel when activeId is stale/foreign to the list", () => {
  const list = [portfolio(1, "Alpha"), portfolio(2, "Beta")];
  assert.equal(resolveActiveLabel(list, 99, "None selected"), "None selected");
});

test("never resolves by list position — id 1 stays Alpha regardless of order", () => {
  const list = [portfolio(2, "Beta"), portfolio(1, "Alpha")];
  assert.equal(resolveActiveLabel(list, 1, "None"), "Alpha");
});

test("returns noneLabel against an empty portfolio list", () => {
  assert.equal(resolveActiveLabel([], 1, "None selected"), "None selected");
});
