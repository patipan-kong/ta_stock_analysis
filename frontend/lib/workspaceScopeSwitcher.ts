// M36.1 Phase 3 — pure helper extracted from WorkspaceScopeSwitcher so its
// identity-resolution logic (never list position, never label, only exact id
// match) can be tested without a DOM/component test runner.

import type { Portfolio } from "@/lib/api";

/**
 * Resolves the display label for the current selection by exact Portfolio
 * Identity (id) match only. Returns `noneLabel` for a null selection or one
 * that no longer resolves against `portfolios` — never falls back to list
 * position (e.g. the first portfolio) or matches by name/label.
 */
export function resolveActiveLabel(
  portfolios: Pick<Portfolio, "id" | "name">[],
  activeId: number | null,
  noneLabel: string
): string {
  if (activeId === null) return noneLabel;
  const match = portfolios.find((p) => p.id === activeId);
  return match ? match.name : noneLabel;
}
