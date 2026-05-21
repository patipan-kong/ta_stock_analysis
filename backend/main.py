import asyncio
import random
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

import os
import json as _json
from models.database import init_db, migrate_legacy_data, get_db, Portfolio, PortfolioItem, Watchlist, AgentCache, AnalysisCache, AnalysisHistory, OptimizerHistory, Settings, UserUsage
from agents.technical import analyze_technical
from agents.fundamental import analyze_fundamental
from agents.news import analyze_news
from agents.summary import analyze_summary
from agents.optimizer import run_optimizer, run_layered_optimizer, _DEFAULT_LAYERS
from agents.chart_data import fetch_chart_data
from services.data_fetcher import fetch_price_info, fetch_info, normalize_dr_symbol
from services.scorer import compute_scores
from services.ai_client import call_ai
from services.json_utils import safe_parse_json
from auth import router as auth_router, verify_token

import sys
try:
    import pysqlite3
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

app = FastAPI(title="Stock Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

_OPEN_PATHS = {"/auth/login", "/docs", "/openapi.json", "/redoc"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.method == "OPTIONS" or request.url.path in _OPEN_PATHS:
        return await call_next(request)
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not verify_token(token):
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)


@app.on_event("startup")
async def startup() -> None:
    init_db()
    migrate_legacy_data()


def _resolve_symbol(symbol: str) -> str:
    s = symbol.upper()
    if "." in s:
        return s
    return s


# ─── AI settings ──────────────────────────────────────────────────────────────

_DEFAULT_AI = {
    "analyze_provider": "anthropic",
    "analyze_model":    "claude-sonnet-4-6",
    "optimize_provider": "anthropic",
    "optimize_model":    "claude-sonnet-4-6",
}
_DEFAULT_SOURCES = {"use_ta": True, "use_fa": True, "use_news": True}


def _get_ai_settings(db: Session) -> dict:
    rows = db.query(Settings).all()
    m = {r.key: r.value for r in rows}
    return {k: m.get(k, v) for k, v in _DEFAULT_AI.items()}


# Per-agent cache TTLs (seconds)
CACHE_TTL = {
    "technical":   60 * 15,       # 15 min  — price/indicator data updates frequently
    "news":        60 * 60,       # 1 hour  — news refresh cadence
    "fundamental": 60 * 60 * 24,  # 24 hours — FA ratios change quarterly
}


def _get_agent_cache(db: Session, symbol: str, agent: str) -> dict | None:
    """Return cached agent result if within TTL, else None."""
    row = db.query(AgentCache).filter_by(symbol=symbol, agent=agent).first()
    if row is None:
        return None
    age = (datetime.utcnow() - row.cached_at).total_seconds()
    if age > CACHE_TTL.get(agent, 60 * 15):
        return None  # stale
    try:
        return _json.loads(row.result_json)
    except Exception:
        return None


def _set_agent_cache(db: Session, symbol: str, agent: str, result: dict) -> None:
    """Upsert agent result into the cache."""
    if not result or "error" in result:
        return  # don't cache error responses
    row = db.query(AgentCache).filter_by(symbol=symbol, agent=agent).first()
    now = datetime.utcnow()
    if row:
        row.result_json = _json.dumps(result)
        row.cached_at = now
    else:
        db.add(AgentCache(symbol=symbol, agent=agent, result_json=_json.dumps(result), cached_at=now))
    db.commit()


def _get_analysis_sources(db: Session) -> dict:
    row = db.query(Settings).filter(Settings.key == "analysis_sources").first()
    if not row:
        return dict(_DEFAULT_SOURCES)
    try:
        saved = _json.loads(row.value)
        return {k: bool(saved.get(k, v)) for k, v in _DEFAULT_SOURCES.items()}
    except Exception:
        return dict(_DEFAULT_SOURCES)


def _upsert_setting(db: Session, key: str, value: str) -> None:
    row = db.query(Settings).filter(Settings.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Settings(key=key, value=value))


# ─── Cache helper ─────────────────────────────────────────────────────────────

def _save_analysis_cache(
    db: Session,
    symbol: str,
    summary: dict,
    technical: dict | None = None,
    fundamental: dict | None = None,
    sources_used: dict | None = None,
) -> None:
    if not summary or "error" in summary:
        return
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    ta_score    = technical.get("ta_score")   if technical   and "error" not in technical   else None
    fa_score    = fundamental.get("fa_score") if fundamental and "error" not in fundamental else None
    ai_provider = summary.get("ai_provider")
    ai_model    = summary.get("ai_model")
    su_json     = _json.dumps(sources_used) if sources_used else None
    existing = db.query(AnalysisCache).filter(AnalysisCache.symbol == symbol).first()
    if existing:
        existing.signal      = summary.get("signal", "HOLD")
        existing.confidence  = summary.get("confidence", "low")
        existing.reasoning   = summary.get("reasoning", "")
        existing.risks       = summary.get("risks", "")
        existing.analyzed_at = now
        if ta_score    is not None: existing.ta_score    = ta_score
        if fa_score    is not None: existing.fa_score    = fa_score
        if ai_provider is not None: existing.ai_provider = ai_provider
        if ai_model    is not None: existing.ai_model    = ai_model
        if su_json     is not None: existing.sources_used = su_json
    else:
        db.add(AnalysisCache(
            symbol=symbol,
            signal=summary.get("signal", "HOLD"),
            confidence=summary.get("confidence", "low"),
            reasoning=summary.get("reasoning", ""),
            risks=summary.get("risks", ""),
            analyzed_at=now,
            ta_score=ta_score, fa_score=fa_score,
            ai_provider=ai_provider, ai_model=ai_model,
            sources_used=su_json,
        ))
    db.commit()


def _save_analysis_history(
    db: Session,
    symbol: str,
    summary: dict,
    technical: dict | None = None,
    fundamental: dict | None = None,
    sources_used: dict | None = None,
    scores: dict | None = None,
    latency_ms: int | None = None,
    total_latency_ms: int | None = None,
) -> AnalysisHistory | None:
    """Always inserts a new history record — never updates."""
    if not summary or "error" in summary:
        return None
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    ta_score = technical.get("ta_score") if technical and "error" not in technical else None
    fa_score = fundamental.get("fa_score") if fundamental and "error" not in fundamental else None
    entry = AnalysisHistory(
        symbol=symbol,
        signal=summary.get("signal", "HOLD"),
        confidence=summary.get("confidence", "low"),
        reasoning=summary.get("reasoning", ""),
        risks=summary.get("risks", ""),
        ta_score=ta_score, fa_score=fa_score,
        ai_provider=summary.get("ai_provider"),
        ai_model=summary.get("ai_model"),
        sources_used=_json.dumps(sources_used) if sources_used else None,
        scores=_json.dumps(scores) if scores else None,
        latency_ms=latency_ms,
        total_latency_ms=total_latency_ms,
        analyzed_at=now,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def _history_row(r: AnalysisHistory) -> dict:
    def _parse(raw: str | None) -> dict | None:
        if not raw:
            return None
        try:
            return _json.loads(raw)
        except Exception:
            return None

    return {
        "id": r.id,
        "symbol": r.symbol,
        "signal": r.signal,
        "confidence": r.confidence,
        "reasoning": r.reasoning,
        "risks": r.risks,
        "ta_score": r.ta_score,
        "fa_score": r.fa_score,
        "ai_provider": r.ai_provider,
        "ai_model": r.ai_model,
        "sources_used": _parse(r.sources_used),
        "scores": _parse(r.scores),
        "analyzed_at": r.analyzed_at.isoformat() + "Z",
    }


THAI_SECTOR_MAP: dict[str, str] = {
    # Financial
    "KBANK.BK": "Financial", "SCB.BK": "Financial", "BBL.BK": "Financial",
    "KTB.BK": "Financial", "BAY.BK": "Financial", "TISCO.BK": "Financial",
    "KKP.BK": "Financial", "TCAP.BK": "Financial", "SAWAD.BK": "Financial",
    "TIDLOR.BK": "Financial", "AEONTS.BK": "Financial", "MBK.BK": "Financial",
    "ASK.BK": "Financial", "JMT.BK": "Financial", "MUTHOOT.BK": "Financial",
    # Energy
    "PTT.BK": "Energy", "PTTEP.BK": "Energy", "PTTGC.BK": "Energy",
    "TOP.BK": "Energy", "IRPC.BK": "Energy", "BCP.BK": "Energy",
    "SPRC.BK": "Energy", "ESSO.BK": "Energy",
    # Utilities
    "BGRIM.BK": "Utilities", "EA.BK": "Utilities", "GPSC.BK": "Utilities",
    "RATCH.BK": "Utilities", "EGCO.BK": "Utilities", "GULF.BK": "Utilities",
    "BANPU.BK": "Utilities", "SPCG.BK": "Utilities",
    # Technology
    "ADVANC.BK": "Technology", "TRUE.BK": "Technology", "INTUCH.BK": "Technology",
    "JASIF.BK": "Technology", "DIF.BK": "Technology", "INTOUCH.BK": "Technology",
    # Industrial/Transport
    "AOT.BK": "Industrial", "AAV.BK": "Industrial", "BEM.BK": "Industrial",
    "BTS.BK": "Industrial", "THAI.BK": "Industrial", "STEC.BK": "Industrial",
    "ITD.BK": "Industrial", "CK.BK": "Industrial", "WHAUP.BK": "Industrial",
    # Consumer
    "CPALL.BK": "Consumer", "BJC.BK": "Consumer", "HMPRO.BK": "Consumer",
    "MAKRO.BK": "Consumer", "CRC.BK": "Consumer", "MINT.BK": "Consumer",
    "ERW.BK": "Consumer", "CENTEL.BK": "Consumer", "OSP.BK": "Consumer",
    "BEAUTY.BK": "Consumer", "OISHI.BK": "Consumer",
    # Healthcare
    "BDMS.BK": "Healthcare", "BH.BK": "Healthcare", "BCH.BK": "Healthcare",
    "PR9.BK": "Healthcare", "VIBHA.BK": "Healthcare", "CHG.BK": "Healthcare",
    "SVH.BK": "Healthcare", "EKH.BK": "Healthcare",
    # Real Estate
    "LH.BK": "Real Estate", "AP.BK": "Real Estate", "SPALI.BK": "Real Estate",
    "CPN.BK": "Real Estate", "SIRI.BK": "Real Estate", "SC.BK": "Real Estate",
    "ORI.BK": "Real Estate", "QH.BK": "Real Estate", "LALIN.BK": "Real Estate",
}


def _get_sector(symbol: str, fa_cache: dict | None) -> str:
    """Resolve sector with three-way branching:
    1. DR stocks (e.g. AAPL01.BK) — FA cache has base-company data fetched via normalize_dr_symbol
    2. Regular Thai stocks (.BK)   — THAI_SECTOR_MAP first, FA cache as fallback
    3. US stocks                   — FA cache (yfinance sector field)
    """
    def _from_cache() -> str | None:
        if fa_cache:
            s = fa_cache.get("sector")
            if s and s not in ("N/A", "Other", ""):
                return s
        return None

    base = normalize_dr_symbol(symbol)
    if base != symbol:
        # DR stock: fundamental data comes from base US ticker, so FA cache already has US sector
        return _from_cache() or "Other"

    if symbol.endswith(".BK"):
        # Regular Thai stock: static map is more reliable than yfinance .BK sector data
        mapped = THAI_SECTOR_MAP.get(symbol)
        if mapped:
            return mapped
        return _from_cache() or "Other"

    # US stock: use FA cache (yfinance sector)
    return _from_cache() or "Other"


async def _fetch_sector(symbol: str) -> str:
    """Resolve sector at add-time. THAI_SECTOR_MAP is free; yfinance is used for DR/US."""
    sector = _get_sector(symbol, None)   # free for THAI_SECTOR_MAP entries
    if sector != "Other":
        return sector
    try:
        normalized = normalize_dr_symbol(symbol)
        info = await asyncio.to_thread(fetch_info, normalized)
        return _get_sector(symbol, info)
    except Exception:
        return "Other"


def _risk_level(ta_score: int | None, fa_score: int | None) -> str | None:
    if ta_score is None and fa_score is None:
        return None
    weighted = round(0.4 * (ta_score or 0) + 0.6 * (fa_score or 0), 1)
    if weighted >= 3:   return "Low"
    if weighted >= 0:   return "Medium"
    if weighted >= -2:  return "High"
    return "Critical"


def _enrich_holdings(
    items: list[PortfolioItem],
    prices: list[dict],
    cached: dict,
    fa_map: dict | None = None,
) -> list[dict]:
    """sector is read directly from the DB column on each PortfolioItem."""
    def _c(sym: str, attr: str, default=None):
        return getattr(cached[sym], attr, default) if sym in cached else default

    result = []
    for item, price in zip(items, prices):
        sym = item.symbol
        ta_score = _c(sym, "ta_score")
        fa_score = _c(sym, "fa_score")
        current_price = price.get("current_price")
        target_price = (fa_map or {}).get(sym)
        upside_pct: float | None = (
            round((target_price - current_price) / current_price * 100, 1)
            if target_price and current_price and current_price > 0
            else None
        )
        result.append({
            "id": item.id,
            "portfolio_id": item.portfolio_id,
            "symbol": sym,
            "shares": item.shares,
            "avg_cost": item.avg_cost,
            **price,
            "latest_signal":    _c(sym, "signal"),
            "signal_confidence": _c(sym, "confidence"),
            "analyzed_at": (_c(sym, "analyzed_at").isoformat() + "Z") if _c(sym, "analyzed_at") else None,
            "reasoning":  _c(sym, "reasoning"),
            "risks":      _c(sym, "risks"),
            "ta_score":   ta_score,
            "fa_score":   fa_score,
            "allow_swap": item.allow_swap,
            "target_price": target_price,
            "upside_pct":   upside_pct,
            "risk_level":   _risk_level(ta_score, fa_score),
            "sector":       item.sector or "Other",
        })
    return result


# ─── Portfolios ───────────────────────────────────────────────────────────────

class PortfolioCreate(BaseModel):
    name: str


@app.get("/portfolios")
async def list_portfolios(db: Session = Depends(get_db)) -> list[dict]:
    items = db.query(Portfolio).order_by(Portfolio.created_at).all()
    return [{"id": p.id, "name": p.name, "cash_balance": p.cash_balance or 0.0, "created_at": p.created_at.isoformat()} for p in items]


@app.post("/portfolios", status_code=201)
async def create_portfolio(body: PortfolioCreate, db: Session = Depends(get_db)) -> dict:
    p = Portfolio(name=body.name.strip())
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id, "name": p.name, "cash_balance": p.cash_balance or 0.0, "created_at": p.created_at.isoformat()}


class CashUpdate(BaseModel):
    cash_balance: float


@app.patch("/portfolios/{portfolio_id}/cash")
async def update_portfolio_cash(portfolio_id: int, body: CashUpdate, db: Session = Depends(get_db)) -> dict:
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    p.cash_balance = max(0.0, body.cash_balance)
    db.commit()
    return {"id": p.id, "cash_balance": p.cash_balance}


@app.delete("/portfolios/{portfolio_id}")
async def delete_portfolio(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if db.query(Portfolio).count() <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last portfolio")
    db.delete(p)
    db.commit()
    return {"deleted": portfolio_id}


# ─── Holdings ─────────────────────────────────────────────────────────────────

class HoldingCreate(BaseModel):
    symbol: str
    shares: float
    avg_cost: float


@app.get("/portfolios/{portfolio_id}/holdings")
async def list_holdings(portfolio_id: int, db: Session = Depends(get_db)) -> list[dict]:
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    items = db.query(PortfolioItem).filter(PortfolioItem.portfolio_id == portfolio_id).all()
    if not items:
        return []
    prices = await asyncio.gather(*[asyncio.to_thread(fetch_price_info, item.symbol) for item in items])
    symbols = [item.symbol for item in items]
    cached = {
        c.symbol: c
        for c in db.query(AnalysisCache).filter(AnalysisCache.symbol.in_(symbols)).all()
    }
    # Read FA AgentCache only for target_price; sector comes from DB column
    fa_map: dict = {}
    for row in db.query(AgentCache).filter(AgentCache.symbol.in_(symbols), AgentCache.agent == "fundamental").all():
        try:
            fa_map[row.symbol] = _json.loads(row.result_json).get("target_price")
        except Exception:
            pass
    return _enrich_holdings(items, prices, cached, fa_map)


@app.get("/portfolios/{portfolio_id}/prices")
async def get_portfolio_prices(portfolio_id: int, db: Session = Depends(get_db)) -> list[dict]:
    """Lightweight real-time price refresh — parallel yfinance fast_info, no AI or cache queries."""
    items = db.query(PortfolioItem).filter(PortfolioItem.portfolio_id == portfolio_id).all()
    if not items:
        return []
    prices = await asyncio.gather(*[asyncio.to_thread(fetch_price_info, item.symbol) for item in items])
    return [{"symbol": item.symbol, **price} for item, price in zip(items, prices)]


@app.get("/portfolios/{portfolio_id}/sector-breakdown")
async def get_sector_breakdown(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    """Return sector allocation for the portfolio with limit status for each sector."""
    items = db.query(PortfolioItem).filter(PortfolioItem.portfolio_id == portfolio_id).all()
    if not items:
        return {"sectors": [], "total_value": 0}

    # Prices (best-effort; fallback to avg_cost)
    prices_list = await asyncio.gather(*[asyncio.to_thread(fetch_price_info, i.symbol) for i in items])
    price_map = {item.symbol: p for item, p in zip(items, prices_list)}

    # Read sector directly from DB column — same source as the portfolio table
    sector_map: dict[str, str] = {item.symbol: item.sector or "Other" for item in items}

    sector_limits = _get_sector_limits(db)
    default_limit: int = int(sector_limits.get("default") or _get_portfolio_settings(db).get("max_sector_pct", 40))

    agg: dict[str, dict] = {}
    for item in items:
        sym = item.symbol
        p = price_map.get(sym, {})
        price = p.get("current_price") or item.avg_cost
        mv = item.shares * price
        sector = sector_map.get(sym, "Other")
        if sector not in agg:
            agg[sector] = {"value": 0.0, "stocks": []}
        agg[sector]["value"] += mv
        agg[sector]["stocks"].append(sym)

    total_value = sum(d["value"] for d in agg.values())
    result = []
    for sector, data in sorted(agg.items(), key=lambda x: -x[1]["value"]):
        weight = round(data["value"] / total_value * 100, 1) if total_value > 0 else 0.0
        limit = int(sector_limits.get(sector) or default_limit)
        status = "EXCEEDS" if weight > limit else "WARNING" if weight > limit * 0.8 else "OK"
        result.append({
            "sector": sector,
            "value": round(data["value"], 2),
            "weight_pct": weight,
            "stocks": data["stocks"],
            "limit_pct": limit,
            "status": status,
        })
    return {"sectors": result, "total_value": round(total_value, 2)}


@app.post("/portfolios/{portfolio_id}/holdings", status_code=201)
async def add_holding(portfolio_id: int, body: HoldingCreate, db: Session = Depends(get_db)) -> dict:
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    symbol = _resolve_symbol(body.symbol)
    existing = db.query(PortfolioItem).filter_by(portfolio_id=portfolio_id, symbol=symbol).first()
    if existing:
        raise HTTPException(status_code=409, detail="Symbol already in this portfolio")
    item = PortfolioItem(portfolio_id=portfolio_id, symbol=symbol, shares=body.shares, avg_cost=body.avg_cost)
    db.add(item)
    db.commit()
    db.refresh(item)
    sector, price = await asyncio.gather(
        _fetch_sector(symbol),
        asyncio.to_thread(fetch_price_info, symbol),
    )
    item.sector = sector
    db.commit()
    return {
        "id": item.id,
        "portfolio_id": item.portfolio_id,
        "symbol": item.symbol,
        "shares": item.shares,
        "avg_cost": item.avg_cost,
        **price,
        "sector": item.sector,
        "latest_signal": None,
        "signal_confidence": None,
        "analyzed_at": None,
        "reasoning": None,
        "risks": None,
        "ta_score": None,
        "fa_score": None,
        "allow_swap": True,
    }


class SwapPermissionBody(BaseModel):
    allow_swap: bool


@app.patch("/portfolios/{portfolio_id}/holdings/{symbol}/swap-permission")
async def update_swap_permission(
    portfolio_id: int, symbol: str, body: SwapPermissionBody, db: Session = Depends(get_db)
) -> dict:
    symbol = _resolve_symbol(symbol)
    item = db.query(PortfolioItem).filter_by(portfolio_id=portfolio_id, symbol=symbol).first()
    if not item:
        raise HTTPException(status_code=404, detail="Symbol not found in this portfolio")
    item.allow_swap = body.allow_swap
    db.commit()
    return {"symbol": symbol, "allow_swap": item.allow_swap}


@app.delete("/portfolios/{portfolio_id}/holdings/{symbol}")
async def remove_holding(portfolio_id: int, symbol: str, db: Session = Depends(get_db)) -> dict:
    symbol = _resolve_symbol(symbol)
    item = db.query(PortfolioItem).filter_by(portfolio_id=portfolio_id, symbol=symbol).first()
    if not item:
        raise HTTPException(status_code=404, detail="Symbol not found in this portfolio")
    db.delete(item)
    db.commit()
    return {"deleted": symbol}


# ─── Watchlist ────────────────────────────────────────────────────────────────

class WatchlistCreate(BaseModel):
    symbol: str


def _watchlist_row(item: Watchlist, cached: dict, target_price: float | None = None, price_info: dict | None = None) -> dict:
    def _c(attr, default=None):
        return getattr(cached[item.symbol], attr, default) if item.symbol in cached else default

    p = price_info or {}
    current_price = p.get("current_price")
    ta_score = _c("ta_score")
    fa_score = _c("fa_score")
    upside_pct: float | None = (
        round((target_price - current_price) / current_price * 100, 1)
        if target_price and current_price and current_price > 0
        else None
    )
    return {
        "id": item.id,
        "symbol": item.symbol,
        "latest_signal":     _c("signal"),
        "signal_confidence": _c("confidence"),
        "analyzed_at": (_c("analyzed_at").isoformat() + "Z") if _c("analyzed_at") else None,
        "reasoning":  _c("reasoning"),
        "risks":      _c("risks"),
        "ta_score":   ta_score,
        "fa_score":   fa_score,
        "target_price": target_price,
        "upside_pct":   upside_pct,
        "risk_level":   _risk_level(ta_score, fa_score),
        "sector":       item.sector or "Other",
    }


@app.get("/watchlist")
async def list_watchlist(db: Session = Depends(get_db)) -> list[dict]:
    items = db.query(Watchlist).order_by(Watchlist.symbol).all()
    if not items:
        return []
    symbols = [i.symbol for i in items]
    cached = {
        c.symbol: c
        for c in db.query(AnalysisCache).filter(AnalysisCache.symbol.in_(symbols)).all()
    }
    # Read FA AgentCache only for target_price; sector comes from DB column
    fa_map: dict[str, float | None] = {}
    for row in db.query(AgentCache).filter(AgentCache.symbol.in_(symbols), AgentCache.agent == "fundamental").all():
        try:
            fa_map[row.symbol] = _json.loads(row.result_json).get("target_price")
        except Exception:
            pass
    # Current prices via fast_info (lightweight)
    prices_list = await asyncio.gather(*[asyncio.to_thread(fetch_price_info, i.symbol) for i in items])
    price_map = {items[j].symbol: p for j, p in enumerate(prices_list)}
    return [
        _watchlist_row(item, cached, fa_map.get(item.symbol), price_map.get(item.symbol))
        for item in items
    ]


@app.post("/watchlist", status_code=201)
async def add_watchlist(body: WatchlistCreate, db: Session = Depends(get_db)) -> dict:
    symbol = _resolve_symbol(body.symbol)
    existing = db.query(Watchlist).filter(Watchlist.symbol == symbol).first()
    if existing:
        raise HTTPException(status_code=409, detail="Symbol already in watchlist")
    item = Watchlist(symbol=symbol)
    db.add(item)
    db.commit()
    db.refresh(item)
    item.sector = await _fetch_sector(symbol)
    db.commit()
    cached = {
        c.symbol: c
        for c in db.query(AnalysisCache).filter(AnalysisCache.symbol == symbol).all()
    }
    return _watchlist_row(item, cached)


@app.delete("/watchlist/{symbol}")
async def remove_watchlist(symbol: str, db: Session = Depends(get_db)) -> dict:
    symbol = _resolve_symbol(symbol)
    item = db.query(Watchlist).filter(Watchlist.symbol == symbol).first()
    if not item:
        raise HTTPException(status_code=404, detail="Symbol not found")
    db.delete(item)
    db.commit()
    return {"deleted": symbol}


# ─── Analysis ────────────────────────────────────────────────────────────────

_CACHE_MAX_AGE = timedelta(hours=12)


def _is_stale(cache: AnalysisCache | None) -> bool:
    if cache is None:
        return True
    return (datetime.utcnow() - cache.analyzed_at) > _CACHE_MAX_AGE


def _parse_sources(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        return _json.loads(raw)
    except Exception:
        return None


def _build_cached_result(symbol: str, cache: AnalysisCache, tech: dict, fund: dict, news: dict) -> dict:
    return {
        "symbol": symbol,
        "technical": tech,
        "fundamental": fund,
        "news": news,
        "sources_used": _parse_sources(cache.sources_used),
        "summary": {
            "symbol": symbol,
            "signal": cache.signal,
            "confidence": cache.confidence,
            "reasoning": cache.reasoning,
            "risks": cache.risks,
            "analyzed_at": cache.analyzed_at.isoformat() + "Z",
            "from_cache": True,
            "ai_provider": cache.ai_provider,
            "ai_model": cache.ai_model,
        },
    }


async def _fetch_agents(
    db: Session,
    symbol: str,
    sources: dict,
) -> tuple[dict | None, dict | None, dict | None]:
    """Fetch tech/fund/news from agent cache when fresh, live otherwise. Parallel for stale agents."""
    tech   = _get_agent_cache(db, symbol, "technical")   if sources.get("use_ta",   True) else None
    fund   = _get_agent_cache(db, symbol, "fundamental") if sources.get("use_fa",   True) else None
    news_r = _get_agent_cache(db, symbol, "news")        if sources.get("use_news", True) else None

    to_run: list[tuple[str, object]] = []
    if sources.get("use_ta",   True) and tech   is None: to_run.append(("technical",   analyze_technical))
    if sources.get("use_fa",   True) and fund   is None: to_run.append(("fundamental", analyze_fundamental))
    if sources.get("use_news", True) and news_r is None: to_run.append(("news",        analyze_news))

    if to_run:
        fresh = await asyncio.gather(*[asyncio.to_thread(fn, symbol) for _, fn in to_run])
        for (name, _), result in zip(to_run, fresh):
            _set_agent_cache(db, symbol, name, result)
            if name == "technical":   tech   = result
            elif name == "fundamental": fund = result
            elif name == "news":      news_r = result

    # Patch FA cache when sector is missing (cache hit from before sector field was added).
    # THAI_SECTOR_MAP lookup is free; DR stocks get "Other" here and need a full re-analysis.
    if fund and "error" not in fund and not fund.get("sector"):
        resolved_sector = _get_sector(symbol, None)
        if resolved_sector != "Other":
            fund["sector"] = resolved_sector
            _set_agent_cache(db, symbol, "fundamental", fund)

    return tech, fund, news_r


async def _run_full_analysis_async(
    db: Session,
    symbol: str,
    provider: str = "anthropic",
    model: str = "claude-sonnet-4-6",
    sources: dict | None = None,
) -> dict:
    if sources is None:
        sources = dict(_DEFAULT_SOURCES)
    import time as _time
    t0 = _time.perf_counter()
    tech, fund, news_r = await _fetch_agents(db, symbol, sources)
    su = {"ta": bool(sources.get("use_ta", True)), "fa": bool(sources.get("use_fa", True)), "news": bool(sources.get("use_news", True))}
    # Compute deterministic scores before AI call so they can anchor the prompt
    scores = compute_scores(tech, fund, news_r)
    summary = await asyncio.to_thread(analyze_summary, symbol, tech, fund, news_r, provider, model, scores)
    total_latency_ms = round((_time.perf_counter() - t0) * 1000)
    return {"symbol": symbol, "technical": tech, "fundamental": fund, "news": news_r, "summary": summary, "sources_used": su, "scores": scores, "total_latency_ms": total_latency_ms}


@app.get("/stocks/{symbol}")
async def get_stock_quick(symbol: str, db: Session = Depends(get_db)) -> dict:
    """Fast path: agent cache (15m/1h/24h TTL) for raw data + cached AI summary.
    Always fetches all three agents for display regardless of analysis source settings."""
    resolved = _resolve_symbol(symbol)
    _all = {"use_ta": True, "use_fa": True, "use_news": True}
    tech, fund, news_result = await _fetch_agents(db, resolved, _all)

    cached = db.query(AnalysisCache).filter(AnalysisCache.symbol == resolved).first()
    summary = None
    if cached:
        summary = {
            "symbol": cached.symbol,
            "signal": cached.signal,
            "confidence": cached.confidence,
            "reasoning": cached.reasoning,
            "risks": cached.risks,
            "analyzed_at": cached.analyzed_at.isoformat() + "Z",
            "from_cache": True,
            "ai_provider": cached.ai_provider,
            "ai_model": cached.ai_model,
        }

    return {
        "symbol": resolved,
        "technical": tech,
        "fundamental": fund,
        "news": news_result,
        "summary": summary,
        "has_cached_summary": summary is not None,
        "sources_used": _parse_sources(cached.sources_used) if cached else None,
    }


@app.get("/analyze/{symbol}")
async def analyze_symbol(symbol: str, db: Session = Depends(get_db)) -> dict:
    resolved = _resolve_symbol(symbol)
    s = _get_ai_settings(db)
    src = _get_analysis_sources(db)
    # Always fetch all agents for display; pass only enabled ones to the AI summary.
    _all = {"use_ta": True, "use_fa": True, "use_news": True}
    tech, fund, news_r = await _fetch_agents(db, resolved, _all)
    ta_ai   = tech  if src.get("use_ta",   True) else None
    fa_ai   = fund  if src.get("use_fa",   True) else None
    news_ai = news_r if src.get("use_news", True) else None
    su = {"ta": bool(src.get("use_ta", True)), "fa": bool(src.get("use_fa", True)), "news": bool(src.get("use_news", True))}
    import time as _time
    t0 = _time.perf_counter()
    sc = compute_scores(tech, fund, news_r)
    summary = await asyncio.to_thread(analyze_summary, resolved, ta_ai, fa_ai, news_ai, s["analyze_provider"], s["analyze_model"], sc)
    total_latency_ms = round((_time.perf_counter() - t0) * 1000)
    _save_analysis_cache(db, resolved, summary, tech, fund, su)
    _save_analysis_history(db, resolved, summary, tech, fund, su, sc,
                           latency_ms=summary.get("latency_ms") if isinstance(summary, dict) else None,
                           total_latency_ms=total_latency_ms)
    if isinstance(summary, dict) and "error" not in summary:
        summary = {**summary, "analyzed_at": datetime.utcnow().isoformat() + "Z", "from_cache": False}
    return {"symbol": resolved, "technical": tech, "fundamental": fund, "news": news_r, "summary": summary, "sources_used": su, "scores": sc}


@app.get("/analyze/{symbol}/technical")
async def analyze_symbol_technical(symbol: str) -> dict:
    return await asyncio.to_thread(analyze_technical, _resolve_symbol(symbol))


@app.get("/analyze/{symbol}/fundamental")
async def analyze_symbol_fundamental(symbol: str) -> dict:
    return await asyncio.to_thread(analyze_fundamental, _resolve_symbol(symbol))


@app.get("/analyze/{symbol}/news")
async def analyze_symbol_news(symbol: str) -> dict:
    return await asyncio.to_thread(analyze_news, _resolve_symbol(symbol))


@app.get("/stocks/{symbol}/chart")
async def get_stock_chart(
    symbol: str,
    period: str = "1d",
    interval: str = "5m",
) -> dict:
    """Return OHLCV candles with EMA20, Bollinger Bands, and RSI for charting."""
    resolved = _resolve_symbol(symbol)
    return await asyncio.to_thread(fetch_chart_data, resolved, period, interval)


@app.post("/portfolios/{portfolio_id}/analyze")
async def analyze_portfolio_holdings(portfolio_id: int, db: Session = Depends(get_db)) -> list[dict]:
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    items = db.query(PortfolioItem).filter(PortfolioItem.portfolio_id == portfolio_id).all()
    symbols = [i.symbol for i in items]
    cache_map = {c.symbol: c for c in db.query(AnalysisCache).filter(AnalysisCache.symbol.in_(symbols)).all()}
    s = _get_ai_settings(db)
    src = _get_analysis_sources(db)
    results = []
    for item in items:
        cache = cache_map.get(item.symbol)
        if _is_stale(cache):
            result = await _run_full_analysis_async(db, item.symbol, s["analyze_provider"], s["analyze_model"], src)
            su = result.get("sources_used")
            sc = result.get("scores")
            _sm = result.get("summary", {})
            _save_analysis_cache(db, item.symbol, _sm, result.get("technical"), result.get("fundamental"), su)
            _save_analysis_history(db, item.symbol, _sm, result.get("technical"), result.get("fundamental"), su, sc,
                                   latency_ms=_sm.get("latency_ms") if isinstance(_sm, dict) else None,
                                   total_latency_ms=result.get("total_latency_ms"))
            if isinstance(_sm, dict) and "error" not in _sm:
                result["summary"] = {**_sm, "analyzed_at": datetime.utcnow().isoformat() + "Z", "from_cache": False}
            results.append(result)
            await asyncio.sleep(random.uniform(1.0, 2.0))
        else:
            tech_r, fund_r, news_r = await _fetch_agents(db, item.symbol, src)
            results.append(_build_cached_result(item.symbol, cache, tech_r, fund_r, news_r))
    return results


@app.post("/analyze/watchlist")
async def analyze_watchlist_all(db: Session = Depends(get_db)) -> list[dict]:
    items = db.query(Watchlist).all()
    symbols = [i.symbol for i in items]
    cache_map = {c.symbol: c for c in db.query(AnalysisCache).filter(AnalysisCache.symbol.in_(symbols)).all()}
    s = _get_ai_settings(db)
    src = _get_analysis_sources(db)
    results = []
    for item in items:
        cache = cache_map.get(item.symbol)
        if _is_stale(cache):
            result = await _run_full_analysis_async(db, item.symbol, s["analyze_provider"], s["analyze_model"], src)
            su = result.get("sources_used")
            sc = result.get("scores")
            _sm = result.get("summary", {})
            _save_analysis_cache(db, item.symbol, _sm, result.get("technical"), result.get("fundamental"), su)
            _save_analysis_history(db, item.symbol, _sm, result.get("technical"), result.get("fundamental"), su, sc,
                                   latency_ms=_sm.get("latency_ms") if isinstance(_sm, dict) else None,
                                   total_latency_ms=result.get("total_latency_ms"))
            if isinstance(_sm, dict) and "error" not in _sm:
                result["summary"] = {**_sm, "analyzed_at": datetime.utcnow().isoformat() + "Z", "from_cache": False}
            results.append(result)
            await asyncio.sleep(random.uniform(1.0, 2.0))
        else:
            tech_r, fund_r, news_r = await _fetch_agents(db, item.symbol, src)
            results.append(_build_cached_result(item.symbol, cache, tech_r, fund_r, news_r))
    return results


# ─── Analyze All (60-min cache) ───────────────────────────────────────────────

_ANALYZE_ALL_TTL = timedelta(hours=1)


def _is_stale_60m(cache: AnalysisCache | None) -> bool:
    if cache is None:
        return True
    return (datetime.utcnow() - cache.analyzed_at) > _ANALYZE_ALL_TTL


async def _analyze_symbol_and_save(db: Session, sym: str, s: dict, src: dict) -> dict:
    result = await _run_full_analysis_async(db, sym, s["analyze_provider"], s["analyze_model"], src)
    su = result.get("sources_used")
    sc = result.get("scores")
    _sm = result.get("summary", {})
    _save_analysis_cache(db, sym, _sm, result.get("technical"), result.get("fundamental"), su)
    _save_analysis_history(db, sym, _sm, result.get("technical"), result.get("fundamental"), su, sc,
                           latency_ms=_sm.get("latency_ms") if isinstance(_sm, dict) else None,
                           total_latency_ms=result.get("total_latency_ms"))
    if isinstance(_sm, dict) and "error" not in _sm:
        result["summary"] = {**_sm, "analyzed_at": datetime.utcnow().isoformat() + "Z", "from_cache": False}
    return result


@app.post("/portfolios/{portfolio_id}/analyze/all")
async def analyze_portfolio_all(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    """Analyze only stale holdings (> 60 min since last analysis). Returns summary counts."""
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    items = db.query(PortfolioItem).filter(PortfolioItem.portfolio_id == portfolio_id).all()
    symbols = [i.symbol for i in items]
    cache_map = {c.symbol: c for c in db.query(AnalysisCache).filter(AnalysisCache.symbol.in_(symbols)).all()}
    s = _get_ai_settings(db)
    src = _get_analysis_sources(db)
    results: list[dict] = []
    skipped_symbols: list[str] = []
    for sym in symbols:
        if _is_stale_60m(cache_map.get(sym)):
            results.append(await _analyze_symbol_and_save(db, sym, s, src))
            await asyncio.sleep(random.uniform(1.0, 2.0))
        else:
            skipped_symbols.append(sym)
    return {
        "total": len(symbols),
        "analyzed": len(results),
        "skipped": len(skipped_symbols),
        "results": results,
        "skipped_symbols": skipped_symbols,
    }


@app.post("/watchlist/analyze/all")
async def analyze_watchlist_60m(db: Session = Depends(get_db)) -> dict:
    """Analyze only stale watchlist symbols (> 60 min since last analysis)."""
    items = db.query(Watchlist).order_by(Watchlist.symbol).all()
    symbols = [i.symbol for i in items]
    cache_map = {c.symbol: c for c in db.query(AnalysisCache).filter(AnalysisCache.symbol.in_(symbols)).all()}
    s = _get_ai_settings(db)
    src = _get_analysis_sources(db)
    results: list[dict] = []
    skipped_symbols: list[str] = []
    for sym in symbols:
        if _is_stale_60m(cache_map.get(sym)):
            results.append(await _analyze_symbol_and_save(db, sym, s, src))
            await asyncio.sleep(random.uniform(1.0, 2.0))
        else:
            skipped_symbols.append(sym)
    return {
        "total": len(symbols),
        "analyzed": len(results),
        "skipped": len(skipped_symbols),
        "results": results,
        "skipped_symbols": skipped_symbols,
    }


# ─── Analysis History ─────────────────────────────────────────────────────────

@app.get("/analysis/history/{symbol}")
async def get_analysis_history(symbol: str, db: Session = Depends(get_db)) -> list[dict]:
    resolved = _resolve_symbol(symbol)
    rows = (
        db.query(AnalysisHistory)
        .filter(AnalysisHistory.symbol == resolved)
        .order_by(AnalysisHistory.analyzed_at.desc())
        .limit(20)
        .all()
    )
    return [_history_row(r) for r in rows]


@app.delete("/analysis/history/{symbol}/{history_id}")
async def delete_analysis_history_entry(
    symbol: str, history_id: int, db: Session = Depends(get_db)
) -> dict:
    resolved = _resolve_symbol(symbol)
    row = db.query(AnalysisHistory).filter(
        AnalysisHistory.id == history_id, AnalysisHistory.symbol == resolved
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="History record not found")
    db.delete(row)
    db.commit()
    return {"deleted": history_id}


# ─── Consensus ───────────────────────────────────────────────────────────────

@app.get("/analyze/{symbol}/consensus")
async def get_consensus(symbol: str, db: Session = Depends(get_db)) -> dict:
    """Aggregate the last 5 analyses for a symbol and report signal agreement."""
    resolved = _resolve_symbol(symbol)
    rows = (
        db.query(AnalysisHistory)
        .filter(AnalysisHistory.symbol == resolved)
        .order_by(AnalysisHistory.analyzed_at.desc())
        .limit(5)
        .all()
    )
    if not rows:
        return {"symbol": resolved, "error": "No analysis history found", "breakdown": []}

    signal_counts: dict[str, int] = {"BUY": 0, "HOLD": 0, "SELL": 0}
    for r in rows:
        if r.signal in signal_counts:
            signal_counts[r.signal] += 1

    total = len(rows)
    dominant = max(signal_counts, key=signal_counts.get)
    agreement = round(signal_counts[dominant] / total, 2)

    breakdown = [_history_row(r) for r in rows]

    return {
        "symbol": resolved,
        "consensus_signal": dominant,
        "agreement": agreement,
        "high_disagreement": agreement < 0.5,
        "total_analyses": total,
        "signal_counts": signal_counts,
        "breakdown": breakdown,
    }


@app.post("/analyze/{symbol}/why-disagree")
async def why_disagree(symbol: str, db: Session = Depends(get_db)) -> dict:
    """Ask Claude to synthesize why recent analyses for this symbol reached different conclusions."""
    resolved = _resolve_symbol(symbol)
    rows = (
        db.query(AnalysisHistory)
        .filter(AnalysisHistory.symbol == resolved)
        .order_by(AnalysisHistory.analyzed_at.desc())
        .limit(5)
        .all()
    )
    if len(rows) < 2:
        return {"error": "Need at least 2 analyses to compare"}

    s = _get_ai_settings(db)
    analyses = [
        {
            "model":    (r.ai_model    or "unknown"),
            "provider": (r.ai_provider or "unknown"),
            "signal":   r.signal,
            "confidence": r.confidence,
            "reasoning":  r.reasoning,
            "risks":      r.risks,
        }
        for r in rows
    ]
    prompt = f"""Multiple AI models analyzed {resolved} and reached these conclusions:

{_json.dumps(analyses, indent=2)}

In 2-3 sentences, synthesize:
1. What key factors cause the disagreement?
2. Which reasoning is most defensible and why?

Return JSON only. No markdown fences.
{{
  "synthesis": "2-3 sentence synthesis of the disagreement",
  "key_differences": ["specific factor 1", "specific factor 2"],
  "most_defensible": "provider/model name and brief reason"
}}"""

    try:
        ai_result = await asyncio.to_thread(
            call_ai,
            prompt,
            s["analyze_provider"],
            s["analyze_model"],
            1024,
            "analyze",
            None,
        )
        parsed = safe_parse_json(ai_result["text"])
        return {"symbol": resolved, **parsed}
    except Exception as exc:
        return {"symbol": resolved, "error": str(exc)}


class OpinionRequest(BaseModel):
    provider: str
    model: str


@app.post("/analyze/{symbol}/opinion")
async def analyze_second_opinion(
    symbol: str, body: OpinionRequest, db: Session = Depends(get_db)
) -> dict:
    """Run analysis with a specific model; saves to history only, not the main cache."""
    resolved = _resolve_symbol(symbol)
    src = _get_analysis_sources(db)
    result = await _run_full_analysis_async(db, resolved, body.provider, body.model, src)
    summary = result.get("summary", {})
    su = result.get("sources_used")
    sc = result.get("scores")
    entry = _save_analysis_history(db, resolved, summary, result.get("technical"), result.get("fundamental"), su, sc,
                                   latency_ms=summary.get("latency_ms") if isinstance(summary, dict) else None,
                                   total_latency_ms=result.get("total_latency_ms"))
    if isinstance(summary, dict) and "error" not in summary:
        result["summary"] = {
            **summary,
            "analyzed_at": datetime.utcnow().isoformat() + "Z",
            "from_cache": False,
            "history_id": entry.id if entry else None,
        }
    return result


class OptimizerRequest(BaseModel):
    portfolio_id: int
    provider: str | None = None
    model: str | None = None


@app.post("/analyze/optimizer")
async def analyze_optimizer(body: OptimizerRequest, db: Session = Depends(get_db)) -> dict:
    """
    Compare a portfolio against the watchlist.
    Runs tech+fund for all symbols (parallel, no Claude per symbol),
    then sends combined scores to Claude for swap suggestions and ranking.
    """
    portfolio = db.query(Portfolio).filter(Portfolio.id == body.portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    holdings = db.query(PortfolioItem).filter(PortfolioItem.portfolio_id == body.portfolio_id).all()
    watchlist_items = db.query(Watchlist).all()

    if not holdings:
        raise HTTPException(status_code=400, detail="Portfolio has no holdings to optimize")
    if not watchlist_items:
        raise HTTPException(status_code=400, detail="Watchlist is empty — add candidates first")

    all_symbols = [h.symbol for h in holdings] + [w.symbol for w in watchlist_items]

    # Fetch cached signals
    cache_map = {
        c.symbol: c
        for c in db.query(AnalysisCache).filter(AnalysisCache.symbol.in_(all_symbols)).all()
    }

    # Run tech+fund for all symbols concurrently (no Claude, ~2s per symbol)
    semaphore = asyncio.Semaphore(5)
    opt_src = _get_analysis_sources(db)

    async def _get_scores(symbol: str) -> dict:
        # Use agent cache; only hit yfinance if stale (semaphore throttles live calls)
        ta_cached = _get_agent_cache(db, symbol, "technical")   if opt_src.get("use_ta", True) else None
        fa_cached = _get_agent_cache(db, symbol, "fundamental") if opt_src.get("use_fa", True) else None
        live_tasks: list[tuple[str, object]] = []
        if opt_src.get("use_ta", True) and ta_cached is None:
            live_tasks.append(("technical", analyze_technical))
        if opt_src.get("use_fa", True) and fa_cached is None:
            live_tasks.append(("fundamental", analyze_fundamental))
        if live_tasks:
            async with semaphore:
                fresh = await asyncio.gather(*[asyncio.to_thread(fn, symbol) for _, fn in live_tasks])
            for (name, _), result in zip(live_tasks, fresh):
                _set_agent_cache(db, symbol, name, result)
                if name == "technical":   ta_cached = result
                elif name == "fundamental": fa_cached = result
        tech, fund = ta_cached, fa_cached
        ta = (tech if tech and "error" not in tech else {}) if opt_src.get("use_ta", True) else {}
        fa = (fund if fund and "error" not in fund else {}) if opt_src.get("use_fa", True) else {}
        c = cache_map.get(symbol)
        ta_score = ta.get("ta_score", 0)
        fa_score = fa.get("fa_score", 0)
        if opt_src.get("use_ta", True) and opt_src.get("use_fa", True):
            combined = round(0.4 * ta_score + 0.6 * fa_score, 1)
        elif opt_src.get("use_fa", True):
            combined = float(fa_score)
        else:
            combined = float(ta_score)
        # Current price + analyst target (lightweight fast_info call)
        price_info = await asyncio.to_thread(fetch_price_info, symbol)
        current_price = price_info.get("current_price")
        target_price  = fa.get("target_price") or price_info.get("target_price")
        upside_pct: float | None = None
        if target_price and current_price and current_price > 0:
            upside_pct = round((target_price - current_price) / current_price * 100, 1)
        return {
            "symbol": symbol,
            "signal":   c.signal if c else "HOLD",
            "combined_score": combined,
            "ta_score": ta_score,
            "fa_score": fa_score,
            "trend":    ta.get("trend", "sideways"),
            "pe_ratio": fa.get("pe_ratio"),
            "roe":      fa.get("roe"),
            "revenue_growth": fa.get("revenue_growth"),
            "fa_summary": fa.get("fa_summary", ""),
            "ta_summary": ta.get("ta_summary", ""),
            "current_price": current_price,
            "target_price":  target_price,
            "upside_pct":    upside_pct,
            "sector":        fa.get("sector") or "Other",
        }

    scores_list = await asyncio.gather(*[_get_scores(sym) for sym in all_symbols])
    scores_map = {s["symbol"]: s for s in scores_list}

    portfolio_data = [
        {**scores_map[h.symbol], "shares": h.shares, "avg_cost": h.avg_cost, "allow_swap": h.allow_swap}
        for h in holdings
        if h.symbol in scores_map
    ]
    watchlist_data = [
        scores_map[w.symbol]
        for w in watchlist_items
        if w.symbol in scores_map
    ]

    ps = _get_portfolio_settings(db)
    max_stocks = ps["max_stocks"]
    max_sector_pct = ps["max_sector_pct"]
    sector_limits = _get_sector_limits(db)
    portfolio_count = len(portfolio_data)
    max_reached = portfolio_count >= max_stocks
    room = max(0, max_stocks - portfolio_count)

    # Compute PE percentiles across all analyzed symbols (portfolio + watchlist)
    all_pe = [(sym, d["pe_ratio"]) for sym, d in scores_map.items()
              if d.get("pe_ratio") and d["pe_ratio"] > 0]
    all_pe.sort(key=lambda x: x[1])
    n_pe = len(all_pe)
    pe_pct = {sym: round(rank / n_pe * 100) for rank, (sym, _) in enumerate(all_pe)} if n_pe > 2 else {}
    for sym in scores_map:
        scores_map[sym]["valuation_percentile"] = pe_pct.get(sym)

    layers = _get_optimizer_layers(db)
    if body.provider:
        layers["layer1"]["provider"] = body.provider
    if body.model:
        layers["layer1"]["model"] = body.model
    result = await asyncio.to_thread(
        run_layered_optimizer, portfolio_data, watchlist_data, portfolio.name,
        portfolio_count, max_reached, layers, max_stocks, max_sector_pct, sector_limits,
    )
    result["portfolio_name"] = portfolio.name
    result["analyzed_at"] = datetime.utcnow().isoformat() + "Z"
    result.setdefault("portfolio_count", portfolio_count)
    result.setdefault("max_reached", max_reached)

    # Enrich watchlist_ranking with upside_pct from pre-fetched scores_map
    upside_map = {sym: d.get("upside_pct") for sym, d in scores_map.items()}
    for item in result.get("watchlist_ranking", []):
        sym = item.get("symbol")
        if sym and item.get("upside_pct") is None:
            item["upside_pct"] = upside_map.get(sym)

    # Hard-enforce: watchlist-only stocks beyond available room get 0% allocation.
    # AI sometimes ignores the cap in the prompt, so we post-process deterministically.
    portfolio_syms = {h.symbol for h in holdings}
    ranking = result.get("watchlist_ranking", [])
    new_stocks = sorted(
        [r for r in ranking if r.get("symbol") not in portfolio_syms],
        key=lambda x: x.get("rank", 999),
    )
    for i, r in enumerate(new_stocks):
        if i >= room:
            r["suggested_allocation_pct"] = 0.0
    # Renormalize remaining non-zero entries so they still sum to 100
    total_alloc = sum(r.get("suggested_allocation_pct", 0) for r in ranking)
    if total_alloc > 0:
        scale = 100.0 / total_alloc
        for r in ranking:
            if r.get("suggested_allocation_pct", 0) > 0:
                r["suggested_allocation_pct"] = round(r["suggested_allocation_pct"] * scale, 1)
    result["watchlist_ranking"] = ranking

    # Persist to history
    entry = OptimizerHistory(
        portfolio_id=body.portfolio_id,
        portfolio_name=portfolio.name,
        analyzed_at=datetime.utcnow(),
        swap_count=len(result.get("swap_suggestions", [])),
        result_json=_json.dumps(result),
        ai_provider=result.get("ai_provider"),
        ai_model=result.get("ai_model"),
        layer1_latency_ms=result.get("layer1_latency_ms"),
        layer2_latency_ms=result.get("layer2_latency_ms"),
        layer3_latency_ms=result.get("layer3_latency_ms"),
        total_latency_ms=result.get("total_latency_ms"),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    result["history_id"] = entry.id
    return result


@app.get("/optimizer/history")
async def list_optimizer_history(portfolio_id: int, db: Session = Depends(get_db)) -> list[dict]:
    rows = (
        db.query(OptimizerHistory)
        .filter(OptimizerHistory.portfolio_id == portfolio_id)
        .order_by(OptimizerHistory.analyzed_at.desc())
        .limit(30)
        .all()
    )
    return [
        {
            "id": r.id,
            "portfolio_name": r.portfolio_name,
            "analyzed_at": r.analyzed_at.isoformat() + "Z",
            "swap_count": r.swap_count,
        }
        for r in rows
    ]


@app.get("/optimizer/history/{history_id}")
async def get_optimizer_history_detail(history_id: int, db: Session = Depends(get_db)) -> dict:
    row = db.query(OptimizerHistory).filter(OptimizerHistory.id == history_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="History not found")
    return _json.loads(row.result_json)


_DEFAULT_PORTFOLIO_SETTINGS = {"max_stocks": 12, "max_sector_pct": 40}
_USD_TO_THB = float(os.getenv("USD_TO_THB_RATE", "36.0"))

_DEFAULT_SECTOR_LIMITS: dict = {
    "Technology":   35,
    "Financial":    30,
    "Energy":       20,
    "Healthcare":   25,
    "Consumer":     25,
    "Industrial":   20,
    "Real Estate":  15,
    "Utilities":    15,
    "default":      25,
}


def _get_sector_limits(db: Session) -> dict:
    row = db.query(Settings).filter(Settings.key == "sector_limits").first()
    if not row:
        return dict(_DEFAULT_SECTOR_LIMITS)
    try:
        saved = _json.loads(row.value)
        result = dict(_DEFAULT_SECTOR_LIMITS)
        result.update({k: int(v) for k, v in saved.items() if isinstance(v, (int, float, str))})
        return result
    except Exception:
        return dict(_DEFAULT_SECTOR_LIMITS)


@app.get("/settings/sector-limits")
async def get_sector_limits(db: Session = Depends(get_db)) -> dict:
    return _get_sector_limits(db)


class SectorLimitsBody(BaseModel):
    limits: dict


@app.patch("/settings/sector-limits")
async def update_sector_limits(body: SectorLimitsBody, db: Session = Depends(get_db)) -> dict:
    current = _get_sector_limits(db)
    for sector, pct in body.limits.items():
        try:
            current[sector] = max(5, min(100, int(pct)))
        except (TypeError, ValueError):
            pass
    _upsert_setting(db, "sector_limits", _json.dumps(current))
    db.commit()
    return current


def _get_portfolio_settings(db: Session) -> dict:
    row = db.query(Settings).filter(Settings.key == "portfolio_settings").first()
    if not row:
        return dict(_DEFAULT_PORTFOLIO_SETTINGS)
    try:
        saved = _json.loads(row.value)
        return {k: int(saved.get(k, v)) for k, v in _DEFAULT_PORTFOLIO_SETTINGS.items()}
    except Exception:
        return dict(_DEFAULT_PORTFOLIO_SETTINGS)


@app.get("/settings/portfolio")
async def get_portfolio_settings(db: Session = Depends(get_db)) -> dict:
    return _get_portfolio_settings(db)


class PortfolioSettingsBody(BaseModel):
    max_stocks: int | None = None
    max_sector_pct: int | None = None


@app.patch("/settings/portfolio")
async def update_portfolio_settings(body: PortfolioSettingsBody, db: Session = Depends(get_db)) -> dict:
    current = _get_portfolio_settings(db)
    if body.max_stocks is not None:
        current["max_stocks"] = max(1, min(30, body.max_stocks))
    if body.max_sector_pct is not None:
        current["max_sector_pct"] = max(10, min(100, body.max_sector_pct))
    _upsert_setting(db, "portfolio_settings", _json.dumps(current))
    db.commit()
    return current


def _get_optimizer_layers(db: Session) -> dict:
    row = db.query(Settings).filter(Settings.key == "optimizer_layers").first()
    if not row:
        return _DEFAULT_LAYERS
    try:
        saved = _json.loads(row.value)
        return {k: {**_DEFAULT_LAYERS[k], **saved.get(k, {})} for k in ("layer1", "layer2", "layer3")}
    except Exception:
        return _DEFAULT_LAYERS


@app.get("/settings/optimizer-layers")
async def get_optimizer_layers(db: Session = Depends(get_db)) -> dict:
    return _get_optimizer_layers(db)


class OptimizerLayerUpdate(BaseModel):
    layer: str
    provider: str
    model: str


@app.patch("/settings/optimizer-layers")
async def update_optimizer_layer(body: OptimizerLayerUpdate, db: Session = Depends(get_db)) -> dict:
    if body.layer not in ("layer1", "layer2", "layer3"):
        raise HTTPException(status_code=400, detail="Invalid layer name")
    row = db.query(Settings).filter(Settings.key == "optimizer_layers").first()
    try:
        current = _json.loads(row.value) if row else {}
    except Exception:
        current = {}
    layers = {k: {**_DEFAULT_LAYERS[k], **current.get(k, {})} for k in ("layer1", "layer2", "layer3")}
    layers[body.layer]["provider"] = body.provider
    layers[body.layer]["model"] = body.model
    _upsert_setting(db, "optimizer_layers", _json.dumps(layers))
    db.commit()
    return layers


@app.get("/ai-models")
async def get_ai_models() -> dict:
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai-model.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return _json.load(f)


class AISettingsBody(BaseModel):
    analyze_provider: str | None = None
    analyze_model: str | None = None
    optimize_provider: str | None = None
    optimize_model: str | None = None


@app.post("/admin/backfill-sectors")
async def backfill_sectors(db: Session = Depends(get_db)) -> dict:
    """Backfill sector column for existing watchlist and portfolio items that are missing it.
    Fetches yfinance info for DR/US stocks; THAI_SECTOR_MAP is used instantly at no cost.
    A 0.3 s pause is added between live yfinance calls to respect rate limits.
    """
    import asyncio as _asyncio

    wl_items  = db.query(Watchlist).filter(
        (Watchlist.sector == None) | (Watchlist.sector == "Other")  # noqa: E711
    ).all()
    pi_items  = db.query(PortfolioItem).filter(
        (PortfolioItem.sector == None) | (PortfolioItem.sector == "Other")  # noqa: E711
    ).all()

    wl_updated = 0
    pi_updated = 0
    failed: list[str] = []
    last_was_live = False  # track whether the previous symbol needed a yfinance call

    async def _resolve(symbol: str) -> str:
        nonlocal last_was_live
        # Free resolution — no yfinance
        sector = _get_sector(symbol, None)
        if sector != "Other":
            last_was_live = False
            return sector
        # Live yfinance call — throttle to avoid rate limits
        if last_was_live:
            await _asyncio.sleep(random.uniform(1.0, 2.0))
        try:
            normalized = normalize_dr_symbol(symbol)
            info = await _asyncio.to_thread(fetch_info, normalized)
            sector = _get_sector(symbol, info)
            last_was_live = True
        except Exception:
            sector = "Other"
            last_was_live = False
        return sector

    for item in wl_items:
        try:
            item.sector = await _resolve(item.symbol)
            wl_updated += 1
        except Exception:
            failed.append(item.symbol)

    for item in pi_items:
        try:
            item.sector = await _resolve(item.symbol)
            pi_updated += 1
        except Exception:
            failed.append(item.symbol)

    if wl_updated or pi_updated:
        db.commit()

    return {
        "watchlist_updated": wl_updated,
        "portfolio_updated": pi_updated,
        "failed": failed,
    }


@app.post("/admin/fix-sectors")
async def fix_sectors(db: Session = Depends(get_db)) -> dict:
    """One-time migration: patch FA agent cache entries with the correct sector field
    so that _get_sector() can use it for DR and US stocks without a live yfinance call.

    For Thai SET stocks in THAI_SECTOR_MAP the sector is always resolved from the map —
    no cache patch needed, but we still report the resolved sector in the response.
    For DR stocks (AAPL01.BK) we resolve via normalize_dr_symbol and update the cached JSON.
    """
    portfolio_syms = {i.symbol for i in db.query(PortfolioItem).all()}
    watchlist_syms = {i.symbol for i in db.query(Watchlist).all()}
    all_symbols = sorted(portfolio_syms | watchlist_syms)

    # Load all existing FA cache entries in one query
    fa_rows: dict[str, AgentCache] = {
        row.symbol: row
        for row in db.query(AgentCache).filter(
            AgentCache.symbol.in_(all_symbols), AgentCache.agent == "fundamental"
        ).all()
    }

    results = []
    updated = 0

    for sym in all_symbols:
        # Cheap resolution first (THAI_SECTOR_MAP + DR normalization — no yfinance call)
        fa_data: dict | None = None
        row = fa_rows.get(sym)
        if row:
            try:
                fa_data = _json.loads(row.result_json)
            except Exception:
                fa_data = None

        sector = _get_sector(sym, fa_data)

        # Patch FA cache JSON if sector is resolved but not stored there yet
        if row and fa_data is not None:
            stored = fa_data.get("sector")
            if sector != "Other" and stored != sector:
                fa_data["sector"] = sector
                row.result_json = _json.dumps(fa_data)
                updated += 1

        results.append({"symbol": sym, "sector": sector, "source": "FA_cache" if fa_data else "map_or_default"})

    if updated:
        db.commit()

    return {"updated": updated, "total": len(all_symbols), "results": results}


@app.get("/stats/latency")
async def get_latency_stats(db: Session = Depends(get_db)) -> dict:
    """Aggregated AI call latency grouped by provider+model (analysis) and provider+model+layer (optimizer)."""
    rows = db.query(UserUsage).all()

    def _p95(vals: list[int]) -> int:
        if not vals:
            return 0
        sv = sorted(vals)
        return sv[min(int(len(sv) * 0.95), len(sv) - 1)]

    analysis_groups: dict[tuple, list] = {}
    analysis_last: dict[tuple, str] = {}
    opt_groups: dict[tuple, list] = {}

    for row in rows:
        if row.latency_ms is None:
            continue
        key2 = (row.provider, row.model)
        if row.operation == "analyze":
            analysis_groups.setdefault(key2, []).append(row.latency_ms)
            if row.created_at:
                analysis_last[key2] = row.created_at.isoformat() + "Z"
        elif row.operation == "optimize":
            key3 = (row.provider, row.model, row.layer or "")
            opt_groups.setdefault(key3, []).append(row.latency_ms)

    analysis_stats = [
        {
            "provider": k[0], "model": k[1],
            "avg_latency_ms": round(sum(v) / len(v)),
            "min_latency_ms": min(v),
            "max_latency_ms": max(v),
            "p95_latency_ms": _p95(v),
            "call_count": len(v),
            "last_used": analysis_last.get(k),
        }
        for k, v in sorted(analysis_groups.items(), key=lambda x: -len(x[1]))
    ]

    opt_stats = [
        {
            "provider": k[0], "model": k[1], "layer": k[2],
            "avg_latency_ms": round(sum(v) / len(v)),
            "call_count": len(v),
        }
        for k, v in sorted(opt_groups.items(), key=lambda x: x[0][2])
    ]

    return {"analysis": analysis_stats, "optimizer": opt_stats}


@app.get("/stats/cost-estimate")
async def get_cost_estimate(db: Session = Depends(get_db)) -> dict:
    """Token usage and cost estimate grouped by provider+model from UserUsage records."""
    rows = db.query(UserUsage).all()
    by_model: dict[str, dict] = {}
    for row in rows:
        key = f"{row.provider}/{row.model}"
        if key not in by_model:
            by_model[key] = {
                "model": row.model,
                "provider": row.provider,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "estimated_cost_usd": 0.0,
                "call_count": 0,
            }
        by_model[key]["total_input_tokens"] += row.input_tokens
        by_model[key]["total_output_tokens"] += row.output_tokens
        by_model[key]["estimated_cost_usd"] += row.total_cost_usd
        by_model[key]["call_count"] += 1

    result_list = sorted(by_model.values(), key=lambda x: -x["estimated_cost_usd"])
    for item in result_list:
        item["estimated_cost_usd"] = round(item["estimated_cost_usd"], 6)

    return {
        "by_model": result_list,
        "total_estimated_usd": round(sum(r["estimated_cost_usd"] for r in result_list), 6),
    }


@app.get("/settings/ai-models")
async def get_ai_settings_endpoint(db: Session = Depends(get_db)) -> dict:
    return _get_ai_settings(db)


@app.patch("/settings/ai-models")
async def update_ai_settings(body: AISettingsBody, db: Session = Depends(get_db)) -> dict:
    for key, value in body.dict(exclude_none=True).items():
        _upsert_setting(db, key, value)
    db.commit()
    return _get_ai_settings(db)


@app.get("/settings/analysis-sources")
async def get_analysis_sources_endpoint(db: Session = Depends(get_db)) -> dict:
    return _get_analysis_sources(db)


class AnalysisSourcesBody(BaseModel):
    use_ta:   bool | None = None
    use_fa:   bool | None = None
    use_news: bool | None = None


@app.patch("/settings/analysis-sources")
async def update_analysis_sources(body: AnalysisSourcesBody, db: Session = Depends(get_db)) -> dict:
    current = _get_analysis_sources(db)
    updates = {k: v for k, v in body.dict().items() if v is not None}
    merged = {**current, **updates}
    _upsert_setting(db, "analysis_sources", _json.dumps(merged))
    db.commit()
    return merged


def _month_bounds_utc(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start, end


def _monthly_total_usd(db: Session, operation: str, start: datetime, end: datetime) -> float:
    total = (
        db.query(func.sum(UserUsage.total_cost_usd))
        .filter(UserUsage.operation == operation)
        .filter(UserUsage.created_at >= start, UserUsage.created_at < end)
        .scalar()
    )
    return float(total or 0.0)


@app.get("/usage/model-cost-report")
async def get_model_cost_report(
    year: int | None = None,
    month: int | None = None,
    db: Session = Depends(get_db),
) -> dict:
    now = datetime.utcnow()
    yy = year or now.year
    mm = month or now.month
    if mm < 1 or mm > 12:
        raise HTTPException(status_code=400, detail="month must be 1-12")

    start, end = _month_bounds_utc(yy, mm)

    analyze_daily_rows = (
        db.query(
            func.date(UserUsage.created_at).label("day"),
            UserUsage.provider,
            UserUsage.model,
            func.sum(UserUsage.input_tokens).label("input_tokens"),
            func.sum(UserUsage.output_tokens).label("output_tokens"),
            func.sum(UserUsage.total_tokens).label("total_tokens"),
            func.sum(UserUsage.total_cost_usd).label("total_cost_usd"),
        )
        .filter(UserUsage.operation == "analyze")
        .filter(UserUsage.created_at >= start, UserUsage.created_at < end)
        .group_by(func.date(UserUsage.created_at), UserUsage.provider, UserUsage.model)
        .order_by(func.date(UserUsage.created_at).asc(), func.sum(UserUsage.total_cost_usd).desc())
        .all()
    )

    analyze_month_rows = (
        db.query(
            UserUsage.provider,
            UserUsage.model,
            func.sum(UserUsage.input_tokens).label("input_tokens"),
            func.sum(UserUsage.output_tokens).label("output_tokens"),
            func.sum(UserUsage.total_tokens).label("total_tokens"),
            func.sum(UserUsage.total_cost_usd).label("total_cost_usd"),
        )
        .filter(UserUsage.operation == "analyze")
        .filter(UserUsage.created_at >= start, UserUsage.created_at < end)
        .group_by(UserUsage.provider, UserUsage.model)
        .order_by(func.sum(UserUsage.total_cost_usd).desc())
        .all()
    )

    optimize_daily_rows = (
        db.query(
            func.date(UserUsage.created_at).label("day"),
            UserUsage.provider,
            UserUsage.model,
            UserUsage.layer,
            func.sum(UserUsage.input_tokens).label("input_tokens"),
            func.sum(UserUsage.output_tokens).label("output_tokens"),
            func.sum(UserUsage.total_tokens).label("total_tokens"),
            func.sum(UserUsage.total_cost_usd).label("total_cost_usd"),
        )
        .filter(UserUsage.operation == "optimize")
        .filter(UserUsage.created_at >= start, UserUsage.created_at < end)
        .group_by(func.date(UserUsage.created_at), UserUsage.provider, UserUsage.model, UserUsage.layer)
        .order_by(func.date(UserUsage.created_at).asc(), func.sum(UserUsage.total_cost_usd).desc())
        .all()
    )

    optimize_month_rows = (
        db.query(
            UserUsage.provider,
            UserUsage.model,
            UserUsage.layer,
            func.sum(UserUsage.input_tokens).label("input_tokens"),
            func.sum(UserUsage.output_tokens).label("output_tokens"),
            func.sum(UserUsage.total_tokens).label("total_tokens"),
            func.sum(UserUsage.total_cost_usd).label("total_cost_usd"),
        )
        .filter(UserUsage.operation == "optimize")
        .filter(UserUsage.created_at >= start, UserUsage.created_at < end)
        .group_by(UserUsage.provider, UserUsage.model, UserUsage.layer)
        .order_by(func.sum(UserUsage.total_cost_usd).desc())
        .all()
    )

    analyze_month_total_usd = _monthly_total_usd(db, "analyze", start, end)
    optimize_month_total_usd = _monthly_total_usd(db, "optimize", start, end)

    return {
        "month": f"{yy:04d}-{mm:02d}",
        "fx": {"usd_to_thb": _USD_TO_THB},
        "analyze": {
            "month_total_usd": round(analyze_month_total_usd, 6),
            "month_total_thb": round(analyze_month_total_usd * _USD_TO_THB, 4),
            "daily": [
                {
                    "date": str(r.day),
                    "provider": r.provider,
                    "model": r.model,
                    "input_tokens": int(r.input_tokens or 0),
                    "output_tokens": int(r.output_tokens or 0),
                    "total_tokens": int(r.total_tokens or 0),
                    "total_cost_usd": round(float(r.total_cost_usd or 0.0), 6),
                    "total_cost_thb": round(float(r.total_cost_usd or 0.0) * _USD_TO_THB, 4),
                }
                for r in analyze_daily_rows
            ],
            "by_model_month": [
                {
                    "provider": r.provider,
                    "model": r.model,
                    "input_tokens": int(r.input_tokens or 0),
                    "output_tokens": int(r.output_tokens or 0),
                    "total_tokens": int(r.total_tokens or 0),
                    "total_cost_usd": round(float(r.total_cost_usd or 0.0), 6),
                    "total_cost_thb": round(float(r.total_cost_usd or 0.0) * _USD_TO_THB, 4),
                }
                for r in analyze_month_rows
            ],
        },
        "optimize": {
            "month_total_usd": round(optimize_month_total_usd, 6),
            "month_total_thb": round(optimize_month_total_usd * _USD_TO_THB, 4),
            "daily": [
                {
                    "date": str(r.day),
                    "provider": r.provider,
                    "model": r.model,
                    "layer": r.layer,
                    "input_tokens": int(r.input_tokens or 0),
                    "output_tokens": int(r.output_tokens or 0),
                    "total_tokens": int(r.total_tokens or 0),
                    "total_cost_usd": round(float(r.total_cost_usd or 0.0), 6),
                    "total_cost_thb": round(float(r.total_cost_usd or 0.0) * _USD_TO_THB, 4),
                }
                for r in optimize_daily_rows
            ],
            "by_model_layer_month": [
                {
                    "provider": r.provider,
                    "model": r.model,
                    "layer": r.layer,
                    "input_tokens": int(r.input_tokens or 0),
                    "output_tokens": int(r.output_tokens or 0),
                    "total_tokens": int(r.total_tokens or 0),
                    "total_cost_usd": round(float(r.total_cost_usd or 0.0), 6),
                    "total_cost_thb": round(float(r.total_cost_usd or 0.0) * _USD_TO_THB, 4),
                }
                for r in optimize_month_rows
            ],
        },
    }


@app.get("/portfolio/{symbol}/latest-signal")
async def get_latest_signal(symbol: str, db: Session = Depends(get_db)) -> dict:
    symbol = _resolve_symbol(symbol)
    cached = db.query(AnalysisCache).filter(AnalysisCache.symbol == symbol).first()
    if not cached:
        return {"symbol": symbol, "signal": None, "confidence": None, "reasoning": None, "risks": None, "analyzed_at": None}
    return {
        "symbol": cached.symbol,
        "signal": cached.signal,
        "confidence": cached.confidence,
        "reasoning": cached.reasoning,
        "risks": cached.risks,
        "analyzed_at": cached.analyzed_at.isoformat() + "Z",
    }
