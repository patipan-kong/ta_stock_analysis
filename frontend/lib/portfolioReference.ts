import type { Portfolio } from "@/lib/api";

/**
 * Resolve a Current Selection candidate against a known Portfolio list.
 *
 * M36-WP1 §5.2: referenceability depends only on exact Portfolio Identity
 * matching within the caller's own workspace — never on availability,
 * lifecycle state, or the fact that a selection was previously persisted.
 * `portfolios` here is already workspace-scoped (listPortfolios() is
 * workspace-scoped server-side), so a plain identity lookup is sufficient.
 */
export function resolvePortfolioReference(portfolios: Portfolio[], id: number | null): Portfolio | null {
  if (id === null) return null;
  return portfolios.find((p) => p.id === id) ?? null;
}
