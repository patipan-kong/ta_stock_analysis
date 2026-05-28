"""Service layer for transaction execution.

Uses Python Decimal internally to avoid float-accumulation errors.
All values stored as Float in DB (SQLite/PostgreSQL compatible).

Supported transaction types:
  BUY              — buy equity; increases holding, reduces cash
  SELL             — sell equity; reduces holding, increases cash
  DEPOSIT          — add cash to portfolio
  WITHDRAW         — remove cash from portfolio (prevents negative balance)
  INITIAL_POSITION — onboarding: import existing holding, does NOT affect cash
  INITIAL_CASH     — onboarding: set starting cash balance
  QUANTITY_CORRECTION — manual share-count adjustment, does NOT affect cash

Fee accounting
--------------
All BUY and SELL fees are calculated via broker_fees.calc_fees():
    Commission   = Gross × 0.15%
    Trading Fee  = Gross × 0.006%
    Clearing Fee = Gross × 0.001%
    VAT          = (Commission + Trading + Clearing) × 7%

Stored in Transaction columns:
    fees  = commission + trading_fee + clearing_fee  (pre-VAT sub-total)
    taxes = VAT amount

Cost basis (BUY)
----------------
Fees are included in the weighted-average cost (fee-inclusive basis):
    effective_price = (gross + total_fees_incl_vat) / shares
    new_avg_cost    = (old_shares × old_avg + new_shares × effective_price)
                      / (old_shares + new_shares)

This means avg_cost already embeds the purchase cost fully, so SELL P/L
only deducts the SELL-side fees—no double-deduction of BUY fees.

Realized P/L (SELL)
-------------------
    realized_pnl = (sell_price - avg_cost) × shares - total_sell_fees_incl_vat

Because avg_cost includes BUY fees, the complete round-trip cost is:
    cost_in  = gross_buy + buy_fees_incl_vat
    cash_out = gross_sell - sell_fees_incl_vat
    true_pnl = cash_out - cost_in  (= the above formula)
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

from sqlalchemy.orm import Session

from models.database import Portfolio, PortfolioItem, Transaction
from services.broker_fees import FeeProfile, FeeBreakdown, calc_fees, resolve_fee_profile

_QUANT = Decimal("0.000001")


def _d(v: float) -> Decimal:
    return Decimal(str(v))


def _f(v: Decimal) -> float:
    return float(v.quantize(_QUANT, rounding=ROUND_HALF_UP))


# ─── BUY ──────────────────────────────────────────────────────────────────────

def execute_buy(
    db: Session,
    ws_id: int,
    portfolio_id: int,
    symbol: str,
    shares: float,
    price_per_share: float,
    currency: str = "THB",
    exchange_rate: float = 1.0,
    transaction_date: datetime | None = None,
    notes: str | None = None,
    sector: str | None = None,
    fee_profile: FeeProfile | None = None,
) -> dict:
    """Create a BUY transaction, upsert the holding, and reduce portfolio cash.

    Fee profile is auto-selected from the symbol (DR vs SET) unless overridden.
    Avg cost uses weighted-average formula with fee-inclusive effective price:
        effective_price = (gross + all_fees) / shares
    Cash is allowed to go negative so users can record purchases before depositing.
    """
    d_shares = _d(shares)
    d_price  = _d(price_per_share)
    d_gross  = d_shares * d_price

    profile  = fee_profile or resolve_fee_profile(symbol)
    bd: FeeBreakdown = calc_fees(d_gross, profile)

    total    = bd.net_buy_amount()                        # cash out
    eff_price = total / d_shares                          # fee-inclusive cost per share

    tx_date = transaction_date or datetime.utcnow()

    item = db.query(PortfolioItem).filter_by(portfolio_id=portfolio_id, symbol=symbol).first()
    if item:
        old_shares = _d(item.shares)
        old_cost   = _d(item.avg_cost)
        new_shares = old_shares + d_shares
        # weighted-average using fee-inclusive total cost of this lot
        new_avg = (old_shares * old_cost + total) / new_shares
        item.shares  = _f(new_shares)
        item.avg_cost = _f(new_avg)
        if sector and not item.sector:
            item.sector = sector
    else:
        item = PortfolioItem(
            workspace_id=ws_id,
            portfolio_id=portfolio_id,
            symbol=symbol,
            shares=_f(d_shares),
            avg_cost=_f(eff_price),       # fee-inclusive from the start
            sector=sector,
        )
        db.add(item)

    portfolio = db.query(Portfolio).filter_by(id=portfolio_id).first()
    if portfolio:
        portfolio.cash_balance = _f(_d(portfolio.cash_balance) - total)

    tx = Transaction(
        workspace_id=ws_id,
        portfolio_id=portfolio_id,
        symbol=symbol,
        transaction_type="BUY",
        shares=_f(d_shares),
        price_per_share=_f(d_price),
        total_amount=_f(total),
        fees=_f(bd.total_fees_excl_vat),   # commission + trading + clearing
        taxes=_f(bd.vat),                  # VAT portion
        currency=currency,
        exchange_rate=exchange_rate,
        transaction_date=tx_date,
        notes=notes,
        sector=sector or (item.sector if item else None),
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    db.refresh(item)

    return {
        "transaction_id": tx.id,
        "type": "BUY",
        "symbol": symbol,
        "shares": tx.shares,
        "price_per_share": tx.price_per_share,
        "gross_amount": _f(d_gross),
        "total_amount": tx.total_amount,
        "fees": tx.fees,
        "taxes": tx.taxes,
        "fee_profile": profile.name,
        "fee_breakdown": bd.to_dict(),
        "transaction_date": tx.transaction_date.isoformat() + "Z",
        "notes": tx.notes,
        "cash_balance": portfolio.cash_balance if portfolio else None,
        "holding": {
            "shares": item.shares,
            "avg_cost": item.avg_cost,
            "sector": item.sector,
        },
    }


# ─── SELL ─────────────────────────────────────────────────────────────────────

def execute_sell(
    db: Session,
    ws_id: int,
    portfolio_id: int,
    symbol: str,
    shares: float,
    price_per_share: float,
    currency: str = "THB",
    exchange_rate: float = 1.0,
    transaction_date: datetime | None = None,
    notes: str | None = None,
    remove_if_zero: bool = True,
    fee_profile: FeeProfile | None = None,
) -> dict:
    """Create a SELL transaction, reduce the holding, and increase portfolio cash.

    Fee profile is auto-selected from the symbol unless overridden.

    Raises ValueError if:
    - No holding exists for the symbol
    - Selling more shares than currently held (oversell prevention)

    Realized P/L = (sell_price - avg_cost) × shares - total_sell_fees_incl_vat
    Because avg_cost already embeds the BUY-side fees, this correctly reflects
    the complete round-trip cost of the position.
    """
    item = db.query(PortfolioItem).filter_by(portfolio_id=portfolio_id, symbol=symbol).first()
    if not item:
        raise ValueError(f"No holding found for {symbol} in this portfolio")

    d_shares = _d(shares)
    d_price  = _d(price_per_share)
    d_gross  = d_shares * d_price
    d_held   = _d(item.shares)

    if d_shares > d_held + Decimal("0.0001"):
        raise ValueError(
            f"Cannot sell {shares} shares of {symbol}; only {item.shares} held"
        )

    profile  = fee_profile or resolve_fee_profile(symbol)
    bd: FeeBreakdown = calc_fees(d_gross, profile)

    net_proceeds = bd.net_sell_proceeds()   # cash in
    d_avg        = _d(item.avg_cost)
    realized_pnl = (d_price - d_avg) * d_shares - bd.total_fees_incl_vat

    tx_date      = transaction_date or datetime.utcnow()
    new_shares   = d_held - d_shares
    holding_removed = False

    pnl_note  = f"Realized P&L: {_f(realized_pnl):+.4f}"
    full_notes = f"{pnl_note}. {notes}" if notes else pnl_note

    if _f(new_shares) <= 0 and remove_if_zero:
        remaining_shares = 0.0
        remaining_avg    = item.avg_cost
        db.delete(item)
        holding_removed  = True
    else:
        item.shares = _f(new_shares)
        remaining_shares = item.shares
        remaining_avg    = item.avg_cost   # avg_cost unchanged on partial sell

    portfolio = db.query(Portfolio).filter_by(id=portfolio_id).first()
    if portfolio:
        portfolio.cash_balance = _f(_d(portfolio.cash_balance) + net_proceeds)

    tx = Transaction(
        workspace_id=ws_id,
        portfolio_id=portfolio_id,
        symbol=symbol,
        transaction_type="SELL",
        shares=_f(d_shares),
        price_per_share=_f(d_price),
        total_amount=_f(abs(net_proceeds)),
        fees=_f(bd.total_fees_excl_vat),
        taxes=_f(bd.vat),
        currency=currency,
        exchange_rate=exchange_rate,
        transaction_date=tx_date,
        notes=full_notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    return {
        "transaction_id": tx.id,
        "type": "SELL",
        "symbol": symbol,
        "shares": tx.shares,
        "price_per_share": tx.price_per_share,
        "gross_amount": _f(d_gross),
        "total_amount": tx.total_amount,
        "fees": tx.fees,
        "taxes": tx.taxes,
        "fee_profile": profile.name,
        "fee_breakdown": bd.to_dict(),
        "realized_pnl": _f(realized_pnl),
        "transaction_date": tx.transaction_date.isoformat() + "Z",
        "notes": tx.notes,
        "holding_removed": holding_removed,
        "cash_balance": portfolio.cash_balance if portfolio else None,
        "holding": None if holding_removed else {
            "shares": remaining_shares,
            "avg_cost": remaining_avg,
        },
    }


# ─── DEPOSIT ──────────────────────────────────────────────────────────────────

def execute_deposit(
    db: Session,
    ws_id: int,
    portfolio_id: int,
    amount: float,
    currency: str = "THB",
    exchange_rate: float = 1.0,
    transaction_date: datetime | None = None,
    notes: str | None = None,
) -> dict:
    """Add cash to the portfolio. No equity holding is affected."""
    if amount <= 0:
        raise ValueError("Deposit amount must be positive")

    d_amount = _d(amount)
    tx_date  = transaction_date or datetime.utcnow()

    portfolio = db.query(Portfolio).filter_by(id=portfolio_id).first()
    if not portfolio:
        raise ValueError("Portfolio not found")

    portfolio.cash_balance = _f(_d(portfolio.cash_balance) + d_amount)

    tx = Transaction(
        workspace_id=ws_id,
        portfolio_id=portfolio_id,
        symbol=None,
        transaction_type="DEPOSIT",
        shares=None,
        price_per_share=None,
        total_amount=_f(d_amount),
        fees=0.0,
        taxes=0.0,
        currency=currency,
        exchange_rate=exchange_rate,
        transaction_date=tx_date,
        notes=notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    return {
        "transaction_id": tx.id,
        "type": "DEPOSIT",
        "symbol": None,
        "amount": tx.total_amount,
        "total_amount": tx.total_amount,
        "transaction_date": tx.transaction_date.isoformat() + "Z",
        "notes": tx.notes,
        "cash_balance": portfolio.cash_balance,
    }


# ─── WITHDRAW ─────────────────────────────────────────────────────────────────

def execute_withdraw(
    db: Session,
    ws_id: int,
    portfolio_id: int,
    amount: float,
    currency: str = "THB",
    exchange_rate: float = 1.0,
    transaction_date: datetime | None = None,
    notes: str | None = None,
) -> dict:
    """Remove cash from the portfolio. Raises ValueError if insufficient cash."""
    if amount <= 0:
        raise ValueError("Withdrawal amount must be positive")

    d_amount = _d(amount)
    tx_date  = transaction_date or datetime.utcnow()

    portfolio = db.query(Portfolio).filter_by(id=portfolio_id).first()
    if not portfolio:
        raise ValueError("Portfolio not found")

    new_cash = _d(portfolio.cash_balance) - d_amount
    if new_cash < Decimal("0"):
        raise ValueError(
            f"Insufficient cash: balance is {portfolio.cash_balance:.2f}, "
            f"cannot withdraw {amount:.2f}"
        )

    portfolio.cash_balance = _f(new_cash)

    tx = Transaction(
        workspace_id=ws_id,
        portfolio_id=portfolio_id,
        symbol=None,
        transaction_type="WITHDRAW",
        shares=None,
        price_per_share=None,
        total_amount=_f(d_amount),
        fees=0.0,
        taxes=0.0,
        currency=currency,
        exchange_rate=exchange_rate,
        transaction_date=tx_date,
        notes=notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    return {
        "transaction_id": tx.id,
        "type": "WITHDRAW",
        "symbol": None,
        "amount": tx.total_amount,
        "total_amount": tx.total_amount,
        "transaction_date": tx.transaction_date.isoformat() + "Z",
        "notes": tx.notes,
        "cash_balance": portfolio.cash_balance,
    }


# ─── DIVIDEND ─────────────────────────────────────────────────────────────────

def execute_dividend(
    db: Session,
    ws_id: int,
    portfolio_id: int,
    symbol: str | None,
    amount: float,
    currency: str = "THB",
    exchange_rate: float = 1.0,
    transaction_date: datetime | None = None,
    notes: str | None = None,
) -> dict:
    """Record a dividend received from a holding. Increases cash balance."""
    if amount <= 0:
        raise ValueError("Dividend amount must be positive")

    d_amount = _d(amount)
    tx_date  = transaction_date or datetime.utcnow()

    portfolio = db.query(Portfolio).filter_by(id=portfolio_id).first()
    if not portfolio:
        raise ValueError("Portfolio not found")

    portfolio.cash_balance = _f(_d(portfolio.cash_balance) + d_amount)

    tx = Transaction(
        workspace_id=ws_id,
        portfolio_id=portfolio_id,
        symbol=symbol,
        transaction_type="DIVIDEND",
        shares=None,
        price_per_share=None,
        total_amount=_f(d_amount),
        fees=0.0,
        taxes=0.0,
        currency=currency,
        exchange_rate=exchange_rate,
        transaction_date=tx_date,
        notes=notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    return {
        "transaction_id": tx.id,
        "type": "DIVIDEND",
        "symbol": symbol,
        "amount": tx.total_amount,
        "total_amount": tx.total_amount,
        "transaction_date": tx.transaction_date.isoformat() + "Z",
        "notes": tx.notes,
        "cash_balance": portfolio.cash_balance,
        "holding": None,
    }


# ─── INITIAL_POSITION ─────────────────────────────────────────────────────────

def execute_initial_position(
    db: Session,
    ws_id: int,
    portfolio_id: int,
    symbol: str,
    shares: float,
    avg_cost: float,
    transaction_date: datetime | None = None,
    notes: str | None = None,
    sector: str | None = None,
) -> dict:
    """Import an existing holding as INITIAL_POSITION.

    Does NOT affect cash balance (this is an onboarding import, not a new trade).
    The avg_cost is taken as-is — no fee adjustment (the original purchase costs
    are unknown at import time).
    """
    if shares <= 0:
        raise ValueError("shares must be positive")
    if avg_cost <= 0:
        raise ValueError("avg_cost must be positive")

    d_shares = _d(shares)
    d_avg    = _d(avg_cost)
    total    = d_shares * d_avg
    tx_date  = transaction_date or datetime.utcnow()

    item = db.query(PortfolioItem).filter_by(portfolio_id=portfolio_id, symbol=symbol).first()
    if item:
        old_shares = _d(item.shares)
        old_cost   = _d(item.avg_cost)
        new_shares = old_shares + d_shares
        new_avg    = (old_shares * old_cost + d_shares * d_avg) / new_shares
        item.shares   = _f(new_shares)
        item.avg_cost = _f(new_avg)
        if sector and not item.sector:
            item.sector = sector
    else:
        item = PortfolioItem(
            workspace_id=ws_id,
            portfolio_id=portfolio_id,
            symbol=symbol,
            shares=_f(d_shares),
            avg_cost=_f(d_avg),
            sector=sector,
        )
        db.add(item)

    tx = Transaction(
        workspace_id=ws_id,
        portfolio_id=portfolio_id,
        symbol=symbol,
        transaction_type="INITIAL_POSITION",
        shares=_f(d_shares),
        price_per_share=_f(d_avg),
        total_amount=_f(total),
        fees=0.0,
        taxes=0.0,
        transaction_date=tx_date,
        notes=notes,
        sector=sector or (item.sector if item else None),
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    db.refresh(item)

    return {
        "transaction_id": tx.id,
        "type": "INITIAL_POSITION",
        "symbol": symbol,
        "shares": tx.shares,
        "price_per_share": tx.price_per_share,
        "total_amount": tx.total_amount,
        "transaction_date": tx.transaction_date.isoformat() + "Z",
        "notes": tx.notes,
        "holding": {
            "shares": item.shares,
            "avg_cost": item.avg_cost,
            "sector": item.sector,
        },
    }


# ─── QUANTITY_CORRECTION ──────────────────────────────────────────────────────

def execute_quantity_correction(
    db: Session,
    ws_id: int,
    portfolio_id: int,
    symbol: str,
    shares_delta: float,
    price_per_share: float,
    transaction_date: datetime | None = None,
    notes: str | None = None,
) -> dict:
    """Apply a share-count correction to an existing position.

    Records a QUANTITY_CORRECTION transaction so the snapshot engine can
    classify the equity change as a balance-sheet event and exclude it from
    investment_return_pct.

    shares_delta may be positive (adding missing shares) or negative
    (removing erroneously recorded shares). avg_cost is recalculated on
    additions using a weighted average.

    Does NOT affect cash_balance — purely a record-keeping correction.
    """
    if shares_delta == 0:
        raise ValueError("shares_delta must be non-zero")
    if price_per_share <= 0:
        raise ValueError("price_per_share must be positive")

    d_delta = _d(shares_delta)
    d_price = _d(price_per_share)
    tx_date = transaction_date or datetime.utcnow()

    item = db.query(PortfolioItem).filter_by(portfolio_id=portfolio_id, symbol=symbol).first()
    if not item:
        raise ValueError(f"No holding found for {symbol} in portfolio {portfolio_id}")

    old_shares = _d(item.shares)
    new_shares = old_shares + d_delta
    if new_shares < 0:
        raise ValueError(
            f"Correction would result in negative shares: {_f(old_shares)} + {_f(d_delta)}"
        )

    if d_delta > 0:
        old_cost = _d(item.avg_cost)
        new_avg  = (old_shares * old_cost + d_delta * d_price) / new_shares
        item.avg_cost = _f(new_avg)

    item.shares = _f(new_shares)

    tx = Transaction(
        workspace_id=ws_id,
        portfolio_id=portfolio_id,
        symbol=symbol,
        transaction_type="QUANTITY_CORRECTION",
        shares=_f(abs(d_delta)),
        price_per_share=_f(d_price),
        total_amount=_f(abs(d_delta) * d_price),
        fees=0.0,
        taxes=0.0,
        transaction_date=tx_date,
        notes=notes or f"Quantity correction: {'+' if d_delta > 0 else ''}{_f(d_delta)} shares",
        sector=item.sector,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    db.refresh(item)

    return {
        "transaction_id": tx.id,
        "type": "QUANTITY_CORRECTION",
        "symbol": symbol,
        "shares_delta": shares_delta,
        "price_per_share": tx.price_per_share,
        "total_amount": tx.total_amount,
        "transaction_date": tx.transaction_date.isoformat() + "Z",
        "notes": tx.notes,
        "holding": {
            "shares": item.shares,
            "avg_cost": item.avg_cost,
            "sector": item.sector,
        },
    }


# ─── INITIAL_CASH ─────────────────────────────────────────────────────────────

def execute_initial_cash(
    db: Session,
    ws_id: int,
    portfolio_id: int,
    amount: float,
    currency: str = "THB",
    transaction_date: datetime | None = None,
    notes: str | None = None,
) -> dict:
    """Set the starting cash for onboarding. Adds to (does not replace) cash balance."""
    if amount <= 0:
        raise ValueError("Initial cash amount must be positive")

    d_amount = _d(amount)
    tx_date  = transaction_date or datetime.utcnow()

    portfolio = db.query(Portfolio).filter_by(id=portfolio_id).first()
    if not portfolio:
        raise ValueError("Portfolio not found")

    portfolio.cash_balance = _f(_d(portfolio.cash_balance) + d_amount)

    tx = Transaction(
        workspace_id=ws_id,
        portfolio_id=portfolio_id,
        symbol=None,
        transaction_type="INITIAL_CASH",
        shares=None,
        price_per_share=None,
        total_amount=_f(d_amount),
        fees=0.0,
        taxes=0.0,
        currency=currency,
        exchange_rate=1.0,
        transaction_date=tx_date,
        notes=notes or "Initial cash balance",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    return {
        "transaction_id": tx.id,
        "type": "INITIAL_CASH",
        "symbol": None,
        "amount": tx.total_amount,
        "total_amount": tx.total_amount,
        "transaction_date": tx.transaction_date.isoformat() + "Z",
        "notes": tx.notes,
        "cash_balance": portfolio.cash_balance,
    }
