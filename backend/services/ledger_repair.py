"""Ledger repair metadata layer — Phase 6.7A Foundation.

Public API
----------
REPAIR_TYPES
    frozenset of valid repair_type strings for Phase 6.7A.

load_active_repairs(db, portfolio_id) -> list[LedgerRepair]
    Load active repair rows for a portfolio from the database, in a
    deterministic order.  Read-only; no side effects.

apply_repair_overlay(canonical_transactions, active_repairs)
    -> (effective_transactions, provenance_map)
    Pure function.  Applies EXCLUDE repairs to produce the effective canonical
    list.  Returns a provenance map covering every original transaction.

Architecture constraints
------------------------
* CanonicalTransaction is frozen (dataclass frozen=True); this module never
  constructs or modifies CanonicalTransaction objects.
* Transaction rows in the database are never mutated by anything in this module.
* apply_repair_overlay has no database access, no network I/O, no side effects.
  Calling it twice with the same inputs always returns identical outputs.
* EXCLUDE is the only repair type that changes the effective canonical list.
  SUPPRESS_FINDING is validated and stored but passes through apply_repair_overlay
  without affecting the list.  Validator integration is Phase 6.7B.
* Unknown repair_type values are silently skipped in apply_repair_overlay as a
  forward-compatibility guard; validation of repair_type happens at insert time.

Phase scope
-----------
Phase 6.7A introduces EXCLUDE and SUPPRESS_FINDING only.
SYMBOL_RENAME, IMPORT_CORRECTION, and LEDGER_EXCEPTION are deferred to
Phase 6.8+ pending resolution of the raw_symbol / holdings_json coupling
identified in the architecture review.
"""
from __future__ import annotations

from typing import Any

from models.database import LedgerRepair
from services.transaction_canonicalizer import CanonicalTransaction

# Exhaustive set of valid repair_type values for Phase 6.7A.
# Inserting any other value must be rejected at the application boundary.
REPAIR_TYPES: frozenset[str] = frozenset({"EXCLUDE", "SUPPRESS_FINDING"})

_PROVENANCE_RAW      = "RAW"
_PROVENANCE_EXCLUDED = "EXCLUDED"


def load_active_repairs(
    db: Any,
    portfolio_id: int,
) -> list[LedgerRepair]:
    """Return all active LedgerRepair rows for a portfolio.

    Order is strictly deterministic: ORDER BY created_at ASC, id ASC.
    apply_repair_overlay processes repairs in this order; callers must not
    assume a different order.

    Args:
        db:           SQLAlchemy Session.
        portfolio_id: Portfolio whose active repairs are loaded.

    Returns:
        List of active LedgerRepair rows, oldest first.  Empty list when the
        portfolio has no active repairs.
    """
    return (
        db.query(LedgerRepair)
        .filter(
            LedgerRepair.portfolio_id == portfolio_id,
            LedgerRepair.is_active.is_(True),
        )
        .order_by(LedgerRepair.created_at, LedgerRepair.id)
        .all()
    )


def apply_repair_overlay(
    canonical_transactions: tuple[CanonicalTransaction, ...],
    active_repairs: list[Any],
) -> tuple[tuple[CanonicalTransaction, ...], dict[int, str]]:
    """Apply an active repair set to a canonical transaction list.

    Pure function: no database access, no network I/O, no side effects.
    Deterministic: same inputs always produce the same outputs.

    Phase 6.7A behaviour
    --------------------
    EXCLUDE
        Removes the targeted transaction from the effective list.  The
        transaction_id referenced by the repair must appear in
        canonical_transactions; if it does not (repair may predate a
        transaction deletion, or reference a wrong portfolio), it is silently
        ignored — the defensive skip prevents a mismatched repair from
        crashing a rebuild.

    SUPPRESS_FINDING
        Carried in active_repairs for future validator integration (Phase 6.7B).
        Does NOT alter the effective canonical list.  Transactions targeted by
        SUPPRESS_FINDING appear in the effective list with provenance "RAW".

    Unknown repair_type
        Silently skipped (forward-compatibility guard).

    Sort invariant
    --------------
    canonical_transactions must already be sorted by (transaction_date, id).
    Removal preserves order; the output tuple is guaranteed to carry the same
    relative ordering as the input.

    Args:
        canonical_transactions:
            Immutable tuple produced by canonicalize_transactions().  Must be
            sorted by (transaction_date, id).
        active_repairs:
            List of LedgerRepair ORM objects — or any objects whose
            .repair_type (str) and .transaction_id (int | None) attributes
            match the LedgerRepair schema.  SimpleNamespace is accepted in
            tests.

    Returns:
        A two-element tuple:

        effective_transactions — tuple[CanonicalTransaction, ...]
            The canonical list with EXCLUDE targets removed.  Same type and
            sort order as the input.  Never None; empty tuple when all
            transactions are excluded.

        provenance_map — dict[int, str]
            Maps every original transaction_id (ctx.id) to its provenance:
              "RAW"      — present in the effective list; no overlay applied.
              "EXCLUDED" — removed from the effective list by an EXCLUDE repair.
            The map always covers every transaction_id in the input tuple; it
            never references transaction_ids outside the input.
    """
    # Collect excluded transaction IDs from all active EXCLUDE repairs.
    # SUPPRESS_FINDING and unknown types are skipped here.
    excluded_ids: set[int] = set()
    for repair in active_repairs:
        if repair.repair_type == "EXCLUDE" and repair.transaction_id is not None:
            excluded_ids.add(repair.transaction_id)

    # Single pass: build effective list and provenance map simultaneously.
    effective: list[CanonicalTransaction] = []
    provenance: dict[int, str] = {}

    for ctx in canonical_transactions:
        if ctx.id in excluded_ids:
            provenance[ctx.id] = _PROVENANCE_EXCLUDED
        else:
            effective.append(ctx)
            provenance[ctx.id] = _PROVENANCE_RAW

    return tuple(effective), provenance
