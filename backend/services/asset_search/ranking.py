"""Market Intelligence — Ranking Engine (Milestone M37.2, WP4).

Implements docs/implementation/M37_1_Universal_Asset_Search_Technical_Design.md
Section 12's ranking model: deterministic ordering of already-produced
candidates. This module ranks; it does not search, does not merge, does not
call providers, does not call `identity_resolver`, and does not write
Registry state — it is a pure function of the candidate lists it is handed
(§3's module-placement table: "pure functions of candidate fields").

Tier order (§12), most-preferred first:
1. Exact canonical/display symbol match — registered only (a
   `DiscoveryCandidate` has no canonical symbol to match against).
2. Exact identifier match (ISIN/CUSIP/SEDOL/FIGI/current provider symbol).
3. Name prefix match — absent until WP1's `AssetDescriptiveName`/
   `Asset.name` ships; no candidate can carry this `match_field` value yet,
   so this tier is a defined-but-currently-empty slot, not invented ranking
   behavior.
4. Name substring match — same staged-conformance note as tier 3.

Within each tier: registered before discovery, then alphabetical by
`canonical_symbol` (registered) / `reported_symbol` (discovery) as the
deterministic tie-break (§12 — "never insertion order, never a
hash-dependent order"). Python's `sorted()` is a stable sort, so candidates
that are still tied after tier/source/symbol keep their relative input
order — this is how registered candidates retain the ordering
`catalog_search.py` (WP2) already established among its own further
tie-break (`canonical_symbol`, then `asset_id`), without `ranking.py`
needing to know about `asset_id` at all.

A candidate missing its tie-break symbol (e.g. a `DiscoveryCandidate` with
`reported_symbol=None`) sorts last within its tier, never first and never
excluded — §8 stage 8: "a candidate missing a rankable field sorts last
within its tier, never excluded."

No provider relevance, no classification-weighted scoring, no
personalization, no analytics/confidence score enters this module — none of
those exist as parameters on `rank()`, so there is nothing to accidentally
wire in later (§12).
"""
from __future__ import annotations

from typing import Any, List, Sequence

from services.asset_search.catalog_search import RegisteredCandidate

__all__ = [
    "rank",
]

# rank() is intentionally duck-typed, not `Sequence[RegisteredCandidate]` —
# per §6/§3, WP4 ranks whatever candidate objects (RegisteredCandidate,
# and later WP6's DiscoveryCandidate) it is handed, without owning or
# importing the discovery-side contract itself. Both candidate types are
# recognized here only by the fields §12's ranking rules actually need
# (`match_field`, and `canonical_symbol`/`reported_symbol` for the
# tie-break) — never by constructing or requiring either concrete class.
Candidate = Any

_SYMBOL_TIER = 0
_IDENTIFIER_TIER = 1
_NAME_PREFIX_TIER = 2
_NAME_SUBSTRING_TIER = 3
_UNRANKED_TIER = 4  # never excluded (§8 stage 8) — sorts last within nothing, i.e. dead last overall


def _tier(candidate: Candidate) -> int:
    """§12's four tiers, keyed off `match_field` — the only field both
    candidate types carry that describes what matched. A candidate whose
    `match_field` matches no known tier (e.g. malformed input, or a
    rankable field simply missing) sorts last, never excluded — ranking
    never fails and never drops a candidate (§8 stage 8)."""
    match_field = candidate.match_field
    if match_field in ("canonical_symbol", "display_symbol"):
        return _SYMBOL_TIER
    if match_field.startswith("identifier:"):
        return _IDENTIFIER_TIER
    if match_field == "name_prefix":
        return _NAME_PREFIX_TIER
    if match_field == "name_substring":
        return _NAME_SUBSTRING_TIER
    return _UNRANKED_TIER


def _source_rank(candidate: Candidate) -> int:
    """Registered before discovery, within a tier (§12)."""
    return 0 if isinstance(candidate, RegisteredCandidate) else 1


def _tie_break_symbol(candidate: Candidate) -> str:
    if isinstance(candidate, RegisteredCandidate):
        return candidate.canonical_symbol or ""
    return candidate.reported_symbol or ""


def rank(candidates: Sequence[Candidate]) -> List[Candidate]:
    """Pure, deterministic ordering of an already-produced candidate list
    per §12. Never touches a database, never calls a provider, never calls
    `identity_resolver`, never mutates a candidate or the input sequence.
    Never raises for any input shape it is actually given — an empty
    sequence returns an empty list; a single candidate returns unchanged."""
    return sorted(
        candidates,
        key=lambda c: (_tier(c), _source_rank(c), not _tie_break_symbol(c), _tie_break_symbol(c)),
    )
