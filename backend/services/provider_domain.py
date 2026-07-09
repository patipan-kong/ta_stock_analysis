"""Asset Registry — Provider Adapter vocabulary (Milestone M4).

Defines the shape provider adapters normalize vendor payloads into, before
any identity-facing translation happens (services/provider_adapter.py).
Kept in its own module rather than appended to resolver_domain.py (M3,
frozen) — same rationale as every prior milestone's own *_domain.py split:
each milestone's file stays frozen once shipped.

ProviderObservation is the canonical, provider-agnostic shape of "what a
provider said about one instrument" (PROVIDER_INTERFACE.md Section 4: "one
canonical model per observation kind", applied here to identity evidence
rather than price). It carries only what a provider might genuinely report;
absent fields are None, never guessed or defaulted (Section 4: "fidelity
plus confession").

ProviderCapabilities is a purely declarative descriptor an adapter attaches
to itself — no routing, selection, or confidence logic reads it yet. It
exists so a future provider-selection or confidence-weighting policy has an
extension point already in place (PROVIDER_INTERFACE.md Section 5:
"declare, don't branch") rather than requiring a breaking change to the
adapter interface later.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import FrozenSet, Optional

from services.asset_domain import IdentifierType


@dataclass(frozen=True)
class ProviderObservation:
    """What one provider reported about one instrument, translated into
    platform vocabulary but not yet a ResolutionClaim. Immutable: this is a
    record of an observation, not working state a caller mutates in place.

    provider_symbol is the vendor's own spelling — evidence, never identity
    (ASSET_REGISTRY.md Section 3). isin/cusip/sedol/figi are populated only
    when the provider actually supplied them; a provider that cannot report
    a field leaves it None rather than the adapter inventing one.
    """

    provider_symbol: Optional[str] = None
    name: Optional[str] = None
    market: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None
    isin: Optional[str] = None
    cusip: Optional[str] = None
    sedol: Optional[str] = None
    figi: Optional[str] = None
    observed_at: Optional[datetime] = None


@dataclass(frozen=True)
class ProviderCapabilities:
    """Declarative-only descriptor of what identity evidence an adapter can
    supply. No behavior is implemented against this today — no router, no
    confidence policy consumes it — it exists purely as a stated extension
    point so a future provider-selection or confidence-weighting policy
    does not require changing the ProviderAdapter interface to add it.

    identifier_types: which IdentifierType values this provider can, in
        principle, supply evidence for (mirrors PROVIDER_INTERFACE.md
        Section 5's capability declarations, scoped to identity).
    supports_search: whether this provider can answer instrument search
        queries at all (distinct from whether M4 wires that up — it
        doesn't; this is a label, not a callable capability).
    """

    identifier_types: FrozenSet[IdentifierType] = frozenset({IdentifierType.PROVIDER_SYMBOL})
    supports_search: bool = False
