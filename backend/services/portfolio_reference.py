"""Shared Portfolio referenceability resolver (M36.1 Phase 0).

M36-WP1 §5.2: a Portfolio Identity is referenceable within a request iff it
has an exact Portfolio Identity match AND belongs to exactly the caller's
workspace — never on Current Selection, availability, lifecycle state, or
generic authority (M36-WP1 foundation invariant 9).

This module consolidates the ~40 identical inline lookups that were
duplicated across backend/main.py:

    p = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.workspace_id == ws
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

into one call. Behavior-preserving by construction: same query, same status
code, same detail string.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.database import Portfolio


def resolve_portfolio_reference(db: Session, portfolio_id: int, workspace_id: int) -> Portfolio | None:
    """Return the Portfolio if it exists and belongs to workspace_id, else None."""
    return (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == workspace_id)
        .first()
    )


def resolve_portfolio_or_404(db: Session, portfolio_id: int, workspace_id: int) -> Portfolio:
    """Return the Portfolio, or raise the standard 404 used across every endpoint."""
    portfolio = resolve_portfolio_reference(db, portfolio_id, workspace_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio
