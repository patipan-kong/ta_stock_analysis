// M36.1 Phase 2 — the explicit fail-closed boundary state for
// portfolio-scoped surfaces. Current Selection (M36-WP1 §9) is zero-or-one
// with no architecture default: when it is NONE, a surface must render this
// instead of issuing any portfolio-scoped request or falling back to
// another portfolio (foundation invariant 11).

export default function PortfolioSelectionNotice({ label }: { label: string }) {
  return (
    <p className="text-sm text-gray-400 py-10 text-center">
      Select a portfolio to view {label}.
    </p>
  );
}
