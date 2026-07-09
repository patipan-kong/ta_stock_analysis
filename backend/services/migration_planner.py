"""Asset Registry — Migration Planner & Dry Run Engine (Milestone M5.1).

Answers one question without changing a single row of production data:
"if we migrate today, what exactly would happen?" (ASSET_REGISTRY_
IMPLEMENTATION_PLAN.md M5.1 success criterion).

This module is an orchestration layer only — the same discipline M5.0's
Evidence Builder held, one level up. It contributes zero new identity
logic:

  - Grouping is the only new concept here (see ClaimShape below). Every
    other step is a call into an already-shipped, unmodified milestone:
    transaction_canonicalizer (M0-era), ledger_evidence_builder (M5.0),
    identity_resolver.resolve() and registry_service.get_asset() (M3/M2).
  - It never calls mint_asset, attach_identifier, record_merge, or
    adjudicate. Only resolve() (read path) and get_asset() (read path)
    are used, per the M5.1 Architecture Requirement: "The planner
    consumes Ledger Evidence Builders, Identity Resolver, Registry
    Service only. The planner must never bypass the Registry."

No writes, enforced structurally rather than by convention
-------------------------------------------------------------
identity_resolver.resolve() is not purely read-only: it durably records a
RegistryFinding row whenever a claim lands AMBIGUOUS or CONFLICT (M3's own
"ambiguity is durable evidence, not a transient return value" design).
Reusing resolve() completely unmodified (ADR-004 — one implementation per
rule; this milestone does not get a resolver-level dry-run flag) while
still honoring "no database mutation, no Registry writes" means the "no
writes" guarantee has to live at the transaction boundary, not the
call-graph boundary: plan_migration() never calls db.commit(), and always
calls db.rollback() in a `finally` block, regardless of outcome. This is
the same shape as M3's own bulk-mode description — "a dry-run report...
without committing anything" — applied literally.

Claim shapes are resolved once, globally, never once per transaction
----------------------------------------------------------------------
The Registry is platform-wide, not portfolio-scoped: two portfolios both
holding "KBANK" priced in the same currency are asking the resolver the
identical identity question. Grouping transactions into ClaimShapes before
calling resolve() — once per distinct shape, across every portfolio in
scope, not once per transaction and not once per portfolio — is required,
not an optimization. Resolving per-transaction would create one duplicate
RegistryFinding per transaction sharing an ambiguity; resolving per
portfolio would still double-count the same ambiguity across portfolios.
Both would misreport "manual adjudications required" even though nothing
here ever commits.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from models.database import Transaction
from services import identity_resolver as resolver
from services import ledger_evidence_builder as evidence_builder
from services import registry_service
from services.resolver_domain import ResolutionResult, ResolutionVerdict
from services.transaction_canonicalizer import canonicalize_transactions

__all__ = [
    "ClaimShape",
    "ClaimShapeResolution",
    "CashOnlyGroup",
    "MigrationPlan",
    "plan_migration",
]


@dataclass(frozen=True)
class ClaimShape:
    """The identity-bearing unit the planner resolves against the Registry.

    Every transaction sharing (raw_symbol, canonical_symbol, currency) is
    one real-world identity question, asked of identity_resolver exactly
    once. Distinct from resolver_domain.ResolutionClaim (M3, unmodified):
    a ClaimShape is the planner's own grouping key over ledger rows, used
    to build exactly one ResolutionClaim per shape; it is never passed to
    the resolver itself and never persisted.

    currency is part of the key, not just a corroboration afterthought:
    the Registry is platform-wide, so the same symbol pair recorded under
    two different transaction currencies is not guaranteed to be the same
    identity question — corroboration scoring depends on it.
    """

    raw_symbol: str
    canonical_symbol: Optional[str]
    currency: Optional[str]


@dataclass(frozen=True)
class ClaimShapeResolution:
    """One ClaimShape's resolution, plus everything the report layer needs
    to describe it without re-deriving anything.

    resolved_market/resolved_exchange/resolved_currency are populated only
    for RESOLVED verdicts, from an explicit registry_service.get_asset()
    read against the winning candidate — never guessed, never inferred
    from the claim's own currency hint. They are the one piece of true
    market/exchange information available anywhere in this milestone,
    since Transaction carries no market/exchange columns of its own.
    """

    shape: ClaimShape
    result: ResolutionResult
    transaction_ids: Tuple[int, ...]
    portfolio_ids: Tuple[int, ...]
    resolved_market: Optional[str] = None
    resolved_exchange: Optional[str] = None
    resolved_currency: Optional[str] = None


@dataclass(frozen=True)
class CashOnlyGroup:
    """Transactions carrying no symbol at all (DEPOSIT/WITHDRAW/
    INITIAL_CASH). These never build a claim and never enter resolver
    classification — they are not an instance of UNKNOWN, which the
    resolver reserves for "evidence present, not decisive". Reported as
    their own bucket so they are never miscounted against the five-way
    verdict split."""

    transaction_ids: Tuple[int, ...]
    portfolio_ids: Tuple[int, ...]


@dataclass(frozen=True)
class MigrationPlan:
    """The planner's complete, immutable output.

    Produced entirely inside a session that is rolled back before this
    object is returned — see plan_migration()'s docstring for why that,
    not a resolver-level flag, is what "no writes" means for this
    milestone."""

    resolutions: Tuple[ClaimShapeResolution, ...]
    cash_only: CashOnlyGroup
    total_transactions: int
    portfolios_scanned: Tuple[int, ...]
    generated_at: datetime


def plan_migration(
    db: Session,
    *,
    portfolio_ids: Optional[Sequence[int]] = None,
    requested_by: str = "migration_planner",
) -> MigrationPlan:
    """Simulates the complete Asset Registry migration for the given
    portfolios (or every portfolio reachable from `db`, if omitted)
    without writing a single row.

    Reuses identity_resolver.resolve() and ledger_evidence_builder
    unmodified (ADR-004) — this function contributes zero new identity
    logic. Its only job: gather ledger evidence, ask the Resolver each
    distinct question exactly once, and hand back a structured answer.

    Always rolls back `db` in `finally`, regardless of outcome, and never
    commits it. Callers must not have uncommitted writes of their own
    pending on `db` before calling this function unless they intend for
    those writes to be discarded too — the rollback applies to the whole
    session, not a savepoint scoped to this call.
    """
    query = db.query(Transaction)
    if portfolio_ids is not None:
        query = query.filter(Transaction.portfolio_id.in_(portfolio_ids))
    transactions = query.all()

    try:
        tx_by_id = {tx.id: tx for tx in transactions}
        canonical = canonicalize_transactions(transactions)

        shape_groups: Dict[ClaimShape, List[int]] = defaultdict(list)
        cash_only_ids: List[int] = []

        for ct in canonical:
            if ct.raw_symbol is None:
                cash_only_ids.append(ct.id)
                continue
            shape = ClaimShape(
                raw_symbol=ct.raw_symbol,
                canonical_symbol=ct.canonical_symbol,
                currency=tx_by_id[ct.id].currency,
            )
            shape_groups[shape].append(ct.id)

        resolutions: List[ClaimShapeResolution] = []
        for shape, tx_ids in shape_groups.items():
            as_of_candidates = [tx_by_id[tid].created_at for tid in tx_ids if tx_by_id[tid].created_at is not None]
            earliest_as_of = min(as_of_candidates) if as_of_candidates else None

            claim = evidence_builder.build_claim(
                shape.raw_symbol,
                shape.canonical_symbol,
                currency=shape.currency,
                as_of=earliest_as_of,
                requested_by=requested_by,
                note=f"M5.1 migration dry run — claim shape {shape.raw_symbol}/{shape.canonical_symbol}",
            )
            result = resolver.resolve(db, claim)

            resolved_market = resolved_exchange = resolved_currency = None
            if result.verdict == ResolutionVerdict.RESOLVED and result.resolved_asset_id is not None:
                asset = registry_service.get_asset(db, result.resolved_asset_id)
                if asset is not None:
                    resolved_market = asset.market
                    resolved_exchange = asset.exchange
                    resolved_currency = asset.currency

            resolutions.append(
                ClaimShapeResolution(
                    shape=shape,
                    result=result,
                    transaction_ids=tuple(sorted(tx_ids)),
                    portfolio_ids=tuple(sorted({tx_by_id[tid].portfolio_id for tid in tx_ids})),
                    resolved_market=resolved_market,
                    resolved_exchange=resolved_exchange,
                    resolved_currency=resolved_currency,
                )
            )

        cash_only = CashOnlyGroup(
            transaction_ids=tuple(sorted(cash_only_ids)),
            portfolio_ids=tuple(sorted({tx_by_id[tid].portfolio_id for tid in cash_only_ids})),
        )

        return MigrationPlan(
            resolutions=tuple(resolutions),
            cash_only=cash_only,
            total_transactions=len(transactions),
            portfolios_scanned=tuple(sorted({tx.portfolio_id for tx in transactions})),
            generated_at=datetime.now(timezone.utc),
        )
    finally:
        db.rollback()
