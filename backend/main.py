import asyncio
import logging
import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

_log = logging.getLogger(__name__)

import os
import json as _json
import uuid as _uuid
from models.database import (
    init_db, migrate_legacy_data, get_db, SessionLocal,
    Workspace, get_default_workspace,
    Portfolio, PortfolioItem, Watchlist,
    AgentCache, AnalysisCache, AnalysisHistory, OptimizerHistory, SignalHistory,
    Settings, UserUsage, Transaction, PortfolioSnapshot, BenchmarkPrice,
)
from agents.technical import analyze_technical
from agents.fundamental import analyze_fundamental
from agents.news import analyze_news
from agents.summary import analyze_summary, determine_signal
from agents.optimizer import run_optimizer, run_layered_optimizer, _DEFAULT_LAYERS
from agents.chart_data import fetch_chart_data
from services.data_fetcher import fetch_price_info, fetch_info, normalize_dr_symbol, is_dr_symbol
from services.scorer import compute_scores
from services.ai_client import call_ai
from services.json_utils import safe_parse_json
from services.portfolio_transactions import (
    execute_buy, execute_sell,
    execute_deposit, execute_withdraw,
    execute_initial_position, execute_initial_cash,
    execute_dividend,
)
from services.portfolio_snapshots import generate_daily_snapshot
from services.snapshot_scheduler import setup_scheduler, shutdown_scheduler
from auth import router as auth_router, verify_token
from routers.scheduler import router as scheduler_router

import sys
try:
    import pysqlite3
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

_ANALYZE_CONCURRENCY = 10
_ANALYZE_SEMAPHORE: asyncio.Semaphore | None = None

# In-process job store: job_id → job state dict.
# Jobs expire after _JOB_TTL_SECONDS (10 min) and are pruned lazily on new job creation.
_JOBS: dict[str, dict] = {}
_JOB_TTL_SECONDS = 600


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _ANALYZE_SEMAPHORE
    _ANALYZE_SEMAPHORE = asyncio.Semaphore(_ANALYZE_CONCURRENCY)
    init_db()
    migrate_legacy_data()
    setup_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="Stock Analysis API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(scheduler_router)

_OPEN_PATHS = {"/auth/login", "/docs", "/openapi.json", "/redoc"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.method == "OPTIONS" or request.url.path in _OPEN_PATHS:
        return await call_next(request)
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not verify_token(token):
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)



def _resolve_symbol(symbol: str) -> str:
    s = symbol.upper()
    if "." in s:
        return s
    return s


def _ws_id(db: Session) -> int:
    """Return the default workspace ID (single-user mode)."""
    return get_default_workspace(db).id


# ─── AI settings ──────────────────────────────────────────────────────────────

_DEFAULT_AI = {
    "analyze_provider": "anthropic",
    "analyze_model":    "claude-sonnet-4-6",
    "optimize_provider": "anthropic",
    "optimize_model":    "claude-sonnet-4-6",
}
_DEFAULT_SOURCES = {"use_ta": True, "use_fa": True, "use_news": True}


def _get_ai_settings(db: Session, ws: int) -> dict:
    rows = db.query(Settings).filter(Settings.workspace_id == ws).all()
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


def _get_analysis_sources(db: Session, ws: int) -> dict:
    row = db.query(Settings).filter(
        Settings.workspace_id == ws,
        Settings.key == "analysis_sources",
    ).first()
    if not row:
        return dict(_DEFAULT_SOURCES)
    try:
        saved = _json.loads(row.value)
        return {k: bool(saved.get(k, v)) for k, v in _DEFAULT_SOURCES.items()}
    except Exception:
        return dict(_DEFAULT_SOURCES)


def _upsert_setting(db: Session, ws: int, key: str, value: str) -> None:
    row = db.query(Settings).filter(
        Settings.workspace_id == ws,
        Settings.key == key,
    ).first()
    if row:
        row.value = value
    else:
        db.add(Settings(workspace_id=ws, key=key, value=value))


# ─── Cache helper ─────────────────────────────────────────────────────────────

def _save_analysis_cache(
    db: Session,
    ws: int,
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
    existing = db.query(AnalysisCache).filter(
        AnalysisCache.workspace_id == ws,
        AnalysisCache.symbol == symbol,
    ).first()
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
            workspace_id=ws,
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
    ws: int,
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
        workspace_id=ws,
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

# Canonical sector keys must match frontend/lib/sectors.ts SECTOR_COLORS
_CANONICAL_SECTORS = frozenset({
    "Technology", "Financial", "Energy", "Healthcare",
    "Consumer", "Industrial", "Real Estate", "Utilities", "Other",
})


def normalize_sector(raw: str | None) -> str:
    """Map raw yfinance/FA sector strings to canonical frontend sector keys."""
    s = (raw or "").strip()
    if s in _CANONICAL_SECTORS:
        return s
    if "Financial" in s:   # "Financial Services" → "Financial"
        return "Financial"
    if "Consumer" in s:    # "Consumer Cyclical", "Consumer Defensive", "Consumer Staples" → "Consumer"
        return "Consumer"
    if "Industrial" in s:  # "Industrials" → "Industrial"
        return "Industrial"
    # "Services", "Basic Materials", "Communication Services", or any unmapped → "Other"
    return "Other"


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
                return normalize_sector(s)
        return None

    base = normalize_dr_symbol(symbol)
    if base != symbol:
        return _from_cache() or "Other"

    if symbol.endswith(".BK"):
        mapped = THAI_SECTOR_MAP.get(symbol)
        if mapped:
            return mapped
        return _from_cache() or "Other"

    return _from_cache() or "Other"


async def _fetch_sector(symbol: str) -> str:
    """Resolve sector at add-time. THAI_SECTOR_MAP is free; yfinance is used for DR/US."""
    sector = _get_sector(symbol, None)
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


def _latest_day_consensus(symbols: list[str], ws: int, db: Session) -> dict[str, dict]:
    """Return {symbol: {signal, confidence}} using only today's (latest day) analyses."""
    if not symbols:
        return {}
    _valid = {"ACCUMULATE", "BUY", "WATCH", "HOLD", "REDUCE", "SELL"}
    recent = (
        db.query(AnalysisHistory)
        .filter(AnalysisHistory.workspace_id == ws, AnalysisHistory.symbol.in_(symbols))
        .order_by(AnalysisHistory.analyzed_at.desc())
        .limit(len(symbols) * 20)
        .all()
    )
    by_symbol: dict[str, list] = {}
    for r in recent:
        by_symbol.setdefault(r.symbol, []).append(r)

    result: dict[str, dict] = {}
    for sym, rows in by_symbol.items():
        latest_date = rows[0].analyzed_at.strftime("%Y-%m-%d")
        day_rows = [r for r in rows if r.analyzed_at.strftime("%Y-%m-%d") == latest_date]
        counts = {s: 0 for s in _valid}
        for r in day_rows:
            if r.signal in counts:
                counts[r.signal] += 1
        dominant = max(counts, key=counts.get)
        conf = next((r.confidence for r in day_rows if r.signal == dominant), day_rows[0].confidence)
        result[sym] = {"signal": dominant, "confidence": conf}
    return result


def _enrich_holdings(
    items: list[PortfolioItem],
    prices: list[dict],
    cached: dict,
    fa_info: dict | None = None,
    parent_prices: dict | None = None,
    consensus_map: dict | None = None,
) -> list[dict]:
    """sector is read directly from the DB column on each PortfolioItem."""
    def _c(sym: str, attr: str, default=None):
        return getattr(cached[sym], attr, default) if sym in cached else default

    result = []
    for item, price in zip(items, prices):
        sym = item.symbol
        ta_score = _c(sym, "ta_score")
        fa_score = _c(sym, "fa_score")
        info = (fa_info or {}).get(sym, {})
        target_price = info.get("target_price")
        is_dr = info.get("is_dr", False)
        parent_sym = info.get("parent_symbol")
        # For DR symbols use parent stock price (USD) for upside; DR local price stays for P/L
        if is_dr and parent_sym and parent_prices:
            upside_price = (parent_prices.get(parent_sym) or {}).get("current_price")
        else:
            upside_price = price.get("current_price")
        upside_pct: float | None = (
            round((target_price - upside_price) / upside_price * 100, 1)
            if target_price and upside_price and upside_price > 0
            else None
        )
        result.append({
            "id": item.id,
            "portfolio_id": item.portfolio_id,
            "symbol": sym,
            "shares": item.shares,
            "avg_cost": item.avg_cost,
            **price,
            "latest_signal":    (consensus_map or {}).get(sym, {}).get("signal") or _c(sym, "signal"),
            "signal_confidence": (consensus_map or {}).get(sym, {}).get("confidence") or _c(sym, "confidence"),
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
            "is_dr":        is_dr,
            "parent_symbol": parent_sym,
            "upside_reference_price": upside_price if is_dr else None,
        })
    return result


# ─── Portfolios ───────────────────────────────────────────────────────────────

class PortfolioCreate(BaseModel):
    name: str


@app.get("/portfolios")
async def list_portfolios(db: Session = Depends(get_db)) -> list[dict]:
    ws = _ws_id(db)
    items = db.query(Portfolio).filter(Portfolio.workspace_id == ws).order_by(Portfolio.created_at).all()
    return [{"id": p.id, "name": p.name, "cash_balance": p.cash_balance or 0.0, "created_at": p.created_at.isoformat()} for p in items]


@app.post("/portfolios", status_code=201)
async def create_portfolio(body: PortfolioCreate, db: Session = Depends(get_db)) -> dict:
    ws = _ws_id(db)
    p = Portfolio(workspace_id=ws, name=body.name.strip())
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id, "name": p.name, "cash_balance": p.cash_balance or 0.0, "created_at": p.created_at.isoformat()}


class CashUpdate(BaseModel):
    cash_balance: float


@app.patch("/portfolios/{portfolio_id}/cash")
async def update_portfolio_cash(portfolio_id: int, body: CashUpdate, db: Session = Depends(get_db)) -> dict:
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    p.cash_balance = max(0.0, body.cash_balance)
    db.commit()
    return {"id": p.id, "cash_balance": p.cash_balance}


@app.delete("/portfolios/{portfolio_id}")
async def delete_portfolio(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if db.query(Portfolio).filter(Portfolio.workspace_id == ws).count() <= 1:
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
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    items = db.query(PortfolioItem).filter(PortfolioItem.portfolio_id == portfolio_id).all()
    if not items:
        return []
    prices = await asyncio.gather(*[asyncio.to_thread(fetch_price_info, item.symbol) for item in items])
    symbols = [item.symbol for item in items]
    cached = {
        c.symbol: c
        for c in db.query(AnalysisCache).filter(
            AnalysisCache.workspace_id == ws,
            AnalysisCache.symbol.in_(symbols),
        ).all()
    }
    fa_info: dict[str, dict] = {}
    for row in db.query(AgentCache).filter(AgentCache.symbol.in_(symbols), AgentCache.agent == "fundamental").all():
        try:
            data = _json.loads(row.result_json)
            dr = is_dr_symbol(row.symbol)
            fa_info[row.symbol] = {
                "target_price": data.get("target_price"),
                "is_dr": dr,
                "parent_symbol": normalize_dr_symbol(row.symbol) if dr else None,
            }
        except Exception:
            pass
    dr_parents = sorted({d["parent_symbol"] for d in fa_info.values() if d.get("is_dr") and d.get("parent_symbol")})
    parent_prices: dict[str, dict] = {}
    if dr_parents:
        pp_list = await asyncio.gather(*[asyncio.to_thread(fetch_price_info, s) for s in dr_parents])
        parent_prices = dict(zip(dr_parents, pp_list))
    consensus_map = _latest_day_consensus(symbols, ws, db)
    return _enrich_holdings(items, prices, cached, fa_info, parent_prices, consensus_map)


@app.get("/portfolios/{portfolio_id}/prices")
async def get_portfolio_prices(portfolio_id: int, db: Session = Depends(get_db)) -> list[dict]:
    """Lightweight real-time price refresh — parallel yfinance fast_info, no AI or cache queries."""
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    items = db.query(PortfolioItem).filter(PortfolioItem.portfolio_id == portfolio_id).all()
    if not items:
        return []
    prices = await asyncio.gather(*[asyncio.to_thread(fetch_price_info, item.symbol) for item in items])
    return [{"symbol": item.symbol, **price} for item, price in zip(items, prices)]


@app.get("/portfolios/{portfolio_id}/sector-breakdown")
async def get_sector_breakdown(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    """Return sector allocation for the portfolio with limit status for each sector."""
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    items = db.query(PortfolioItem).filter(PortfolioItem.portfolio_id == portfolio_id).all()
    if not items:
        return {"sectors": [], "total_value": 0}

    prices_list = await asyncio.gather(*[asyncio.to_thread(fetch_price_info, i.symbol) for i in items])
    price_map = {item.symbol: p for item, p in zip(items, prices_list)}

    sector_map: dict[str, str] = {item.symbol: normalize_sector(item.sector) for item in items}

    sector_limits = _get_sector_limits(db, ws)
    default_limit: int = int(sector_limits.get("default") or _get_portfolio_settings(db, ws).get("max_sector_pct", 40))

    agg: dict[str, dict] = {}
    for item in items:
        sym = item.symbol
        pr = price_map.get(sym, {})
        price = pr.get("current_price") or item.avg_cost
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
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    symbol = _resolve_symbol(body.symbol)
    existing = db.query(PortfolioItem).filter_by(portfolio_id=portfolio_id, symbol=symbol).first()
    if existing:
        raise HTTPException(status_code=409, detail="Symbol already in this portfolio")
    item = PortfolioItem(workspace_id=ws, portfolio_id=portfolio_id, symbol=symbol, shares=body.shares, avg_cost=body.avg_cost)
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
    ws = _ws_id(db)
    symbol = _resolve_symbol(symbol)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    item = db.query(PortfolioItem).filter_by(portfolio_id=portfolio_id, symbol=symbol).first()
    if not item:
        raise HTTPException(status_code=404, detail="Symbol not found in this portfolio")
    item.allow_swap = body.allow_swap
    db.commit()
    return {"symbol": symbol, "allow_swap": item.allow_swap}


@app.delete("/portfolios/{portfolio_id}/holdings/{symbol}")
async def remove_holding(portfolio_id: int, symbol: str, db: Session = Depends(get_db)) -> dict:
    ws = _ws_id(db)
    symbol = _resolve_symbol(symbol)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    item = db.query(PortfolioItem).filter_by(portfolio_id=portfolio_id, symbol=symbol).first()
    if not item:
        raise HTTPException(status_code=404, detail="Symbol not found in this portfolio")
    db.delete(item)
    db.commit()
    return {"deleted": symbol}


# ─── Watchlist ────────────────────────────────────────────────────────────────

class WatchlistCreate(BaseModel):
    symbol: str


def _watchlist_row(
    item: Watchlist,
    cached: dict,
    fa_info_item: dict | None = None,
    price_info: dict | None = None,
    parent_price: dict | None = None,
) -> dict:
    def _c(attr, default=None):
        return getattr(cached[item.symbol], attr, default) if item.symbol in cached else default

    p = price_info or {}
    fi = fa_info_item or {}
    target_price = fi.get("target_price")
    is_dr = fi.get("is_dr", False)
    parent_sym = fi.get("parent_symbol")
    ta_score = _c("ta_score")
    fa_score = _c("fa_score")
    if is_dr and parent_sym and parent_price:
        upside_price = parent_price.get("current_price")
    else:
        upside_price = p.get("current_price")
    upside_pct: float | None = (
        round((target_price - upside_price) / upside_price * 100, 1)
        if target_price and upside_price and upside_price > 0
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
        "is_dr":        is_dr,
        "parent_symbol": parent_sym,
        "upside_reference_price": upside_price if is_dr else None,
    }


@app.get("/watchlist")
async def list_watchlist(db: Session = Depends(get_db)) -> list[dict]:
    ws = _ws_id(db)
    items = db.query(Watchlist).filter(Watchlist.workspace_id == ws).order_by(Watchlist.symbol).all()
    if not items:
        return []
    symbols = [i.symbol for i in items]
    cached = {
        c.symbol: c
        for c in db.query(AnalysisCache).filter(
            AnalysisCache.workspace_id == ws,
            AnalysisCache.symbol.in_(symbols),
        ).all()
    }
    fa_info: dict[str, dict] = {}
    for row in db.query(AgentCache).filter(AgentCache.symbol.in_(symbols), AgentCache.agent == "fundamental").all():
        try:
            data = _json.loads(row.result_json)
            dr = is_dr_symbol(row.symbol)
            fa_info[row.symbol] = {
                "target_price": data.get("target_price"),
                "is_dr": dr,
                "parent_symbol": normalize_dr_symbol(row.symbol) if dr else None,
            }
        except Exception:
            pass
    prices_list = await asyncio.gather(*[asyncio.to_thread(fetch_price_info, i.symbol) for i in items])
    price_map = {items[j].symbol: p for j, p in enumerate(prices_list)}
    dr_parents = sorted({d["parent_symbol"] for d in fa_info.values() if d.get("is_dr") and d.get("parent_symbol")})
    parent_prices: dict[str, dict] = {}
    if dr_parents:
        pp_list = await asyncio.gather(*[asyncio.to_thread(fetch_price_info, s) for s in dr_parents])
        parent_prices = dict(zip(dr_parents, pp_list))
    return [
        _watchlist_row(
            item, cached,
            fa_info.get(item.symbol),
            price_map.get(item.symbol),
            parent_prices.get(fa_info.get(item.symbol, {}).get("parent_symbol", ""), {}),
        )
        for item in items
    ]


@app.post("/watchlist", status_code=201)
async def add_watchlist(body: WatchlistCreate, db: Session = Depends(get_db)) -> dict:
    ws = _ws_id(db)
    symbol = _resolve_symbol(body.symbol)
    existing = db.query(Watchlist).filter(
        Watchlist.workspace_id == ws,
        Watchlist.symbol == symbol,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Symbol already in watchlist")
    item = Watchlist(workspace_id=ws, symbol=symbol)
    db.add(item)
    db.commit()
    db.refresh(item)
    item.sector = await _fetch_sector(symbol)
    db.commit()
    cached = {
        c.symbol: c
        for c in db.query(AnalysisCache).filter(
            AnalysisCache.workspace_id == ws,
            AnalysisCache.symbol == symbol,
        ).all()
    }
    return _watchlist_row(item, cached)


@app.delete("/watchlist/{symbol}")
async def remove_watchlist(symbol: str, db: Session = Depends(get_db)) -> dict:
    ws = _ws_id(db)
    symbol = _resolve_symbol(symbol)
    item = db.query(Watchlist).filter(
        Watchlist.workspace_id == ws,
        Watchlist.symbol == symbol,
    ).first()
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


def _ndjson(obj: dict) -> str:
    return _json.dumps(obj, ensure_ascii=False) + "\n"


def _build_fallback_result(
    symbol: str,
    tech: dict | None,
    fund: dict | None,
    news_r: dict | None,
    scores: dict,
    sources_used: dict,
    elapsed_ms: int,
    reason: str,
) -> dict:
    """Deterministic signal result used when AI call times out or errors."""
    ta_short = (tech or {}).get("short_term", {}).get("score") if tech and "error" not in tech else None
    ta_long  = (tech or {}).get("long_term",  {}).get("score") if tech and "error" not in tech else None
    fa_score = (fund or {}).get("fa_score")                    if fund and "error" not in fund else None
    signal, confidence = determine_signal(ta_short, ta_long, fa_score)
    return {
        "symbol": symbol,
        "technical": tech,
        "fundamental": fund,
        "news": news_r,
        "summary": {
            "symbol": symbol,
            "signal": signal,
            "confidence": confidence,
            "reasoning": f"Deterministic fallback — {reason}",
            "risks": "AI analysis unavailable",
            "ai_fallback_used": True,
            "latency_ms": 0,
        },
        "sources_used": sources_used,
        "scores": scores,
        "total_latency_ms": elapsed_ms,
        "ai_fallback_used": True,
    }


def _cleanup_jobs() -> None:
    """Prune jobs older than _JOB_TTL_SECONDS from the in-process store."""
    now = datetime.utcnow()
    expired = [
        jid for jid, j in _JOBS.items()
        if (now - j["created_at"]).total_seconds() > _JOB_TTL_SECONDS
    ]
    for jid in expired:
        del _JOBS[jid]


async def _run_analysis_job(job_id: str, ws: int, stale_syms: list[str], s: dict, src: dict) -> None:
    """Background task: runs concurrent analysis for all stale symbols, updating _JOBS as each finishes."""
    job = _JOBS.get(job_id)
    if not job:
        return
    total = len(stale_syms)
    job["status"] = "running"
    if total == 0:
        job["status"] = "done"
        return

    queue: asyncio.Queue = asyncio.Queue()

    async def _worker(sym: str) -> None:
        result = await _analyze_one_concurrent(ws, sym, s, src)
        await queue.put(result)

    for sym in stale_syms:
        asyncio.create_task(_worker(sym))

    fallbacks = 0
    for _ in range(total):
        result = await queue.get()
        if result.get("ai_fallback_used"):
            fallbacks += 1
        job["done"] += 1
        job["fallbacks"] = fallbacks
        job["results"].append(result)

    job["status"] = "done"
    _log.info("[job:%s] done — %d analyzed, %d fallbacks", job_id, total, fallbacks)


async def _analyze_one_concurrent(ws: int, sym: str, s: dict, src: dict) -> dict:
    """
    Analyze a single symbol with its own DB session.
    Concurrency is capped by _ANALYZE_SEMAPHORE (10 max).
    AI call is wrapped in a 10 s timeout; on expiry returns a deterministic fallback.
    """
    import time as _time
    t0 = _time.perf_counter()
    su = {
        "ta":   bool(src.get("use_ta",   True)),
        "fa":   bool(src.get("use_fa",   True)),
        "news": bool(src.get("use_news", True)),
    }

    assert _ANALYZE_SEMAPHORE is not None
    async with _ANALYZE_SEMAPHORE:
        db = SessionLocal()
        try:
            tech, fund, news_r = await _fetch_agents(db, sym, src)
            scores = compute_scores(tech, fund, news_r)

            try:
                summary = await asyncio.wait_for(
                    asyncio.to_thread(
                        analyze_summary, sym, tech, fund, news_r,
                        s["analyze_provider"], s["analyze_model"], scores,
                    ),
                    timeout=10.0,
                )
            except asyncio.TimeoutError:
                elapsed_ms = round((_time.perf_counter() - t0) * 1000)
                _log.warning("[analyze_concurrent] %s AI timeout after %d ms", sym, elapsed_ms)
                return _build_fallback_result(sym, tech, fund, news_r, scores, su, elapsed_ms, "AI timeout")

            total_latency_ms = round((_time.perf_counter() - t0) * 1000)
            _log.debug("[analyze_concurrent] %s done in %d ms", sym, total_latency_ms)

            _sm = summary
            _save_analysis_cache(db, ws, sym, _sm, tech, fund, su)
            _save_analysis_history(
                db, ws, sym, _sm, tech, fund, su, scores,
                latency_ms=_sm.get("latency_ms") if isinstance(_sm, dict) else None,
                total_latency_ms=total_latency_ms,
            )
            if isinstance(_sm, dict) and "error" not in _sm:
                summary = {**_sm, "analyzed_at": datetime.utcnow().isoformat() + "Z", "from_cache": False}

            return {
                "symbol": sym,
                "technical": tech,
                "fundamental": fund,
                "news": news_r,
                "summary": summary,
                "sources_used": su,
                "scores": scores,
                "total_latency_ms": total_latency_ms,
            }

        except Exception as exc:
            elapsed_ms = round((_time.perf_counter() - t0) * 1000)
            _log.warning("[analyze_concurrent] %s error after %d ms: %s", sym, elapsed_ms, exc)
            return _build_fallback_result(sym, None, None, None, {}, su, elapsed_ms, str(exc))

        finally:
            db.close()


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
    scores = compute_scores(tech, fund, news_r)
    summary = await asyncio.to_thread(analyze_summary, symbol, tech, fund, news_r, provider, model, scores)
    total_latency_ms = round((_time.perf_counter() - t0) * 1000)
    return {"symbol": symbol, "technical": tech, "fundamental": fund, "news": news_r, "summary": summary, "sources_used": su, "scores": scores, "total_latency_ms": total_latency_ms}


@app.get("/stocks/{symbol}")
async def get_stock_quick(symbol: str, db: Session = Depends(get_db)) -> dict:
    """Fast path: agent cache (15m/1h/24h TTL) for raw data + cached AI summary."""
    ws = _ws_id(db)
    resolved = _resolve_symbol(symbol)
    _all = {"use_ta": True, "use_fa": True, "use_news": True}
    tech, fund, news_result = await _fetch_agents(db, resolved, _all)

    cached = db.query(AnalysisCache).filter(
        AnalysisCache.workspace_id == ws,
        AnalysisCache.symbol == resolved,
    ).first()
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
    ws = _ws_id(db)
    resolved = _resolve_symbol(symbol)
    s = _get_ai_settings(db, ws)
    src = _get_analysis_sources(db, ws)
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
    _save_analysis_cache(db, ws, resolved, summary, tech, fund, su)
    _save_analysis_history(db, ws, resolved, summary, tech, fund, su, sc,
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
    resolved = _resolve_symbol(symbol)
    return await asyncio.to_thread(fetch_chart_data, resolved, period, interval)


@app.post("/portfolios/{portfolio_id}/analyze")
async def analyze_portfolio_holdings(portfolio_id: int, db: Session = Depends(get_db)) -> list[dict]:
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    items = db.query(PortfolioItem).filter(PortfolioItem.portfolio_id == portfolio_id).all()
    symbols = [i.symbol for i in items]
    cache_map = {
        c.symbol: c
        for c in db.query(AnalysisCache).filter(
            AnalysisCache.workspace_id == ws,
            AnalysisCache.symbol.in_(symbols),
        ).all()
    }
    s = _get_ai_settings(db, ws)
    src = _get_analysis_sources(db, ws)
    results = []
    for item in items:
        cache = cache_map.get(item.symbol)
        if _is_stale(cache):
            result = await _run_full_analysis_async(db, item.symbol, s["analyze_provider"], s["analyze_model"], src)
            su = result.get("sources_used")
            sc = result.get("scores")
            _sm = result.get("summary", {})
            _save_analysis_cache(db, ws, item.symbol, _sm, result.get("technical"), result.get("fundamental"), su)
            _save_analysis_history(db, ws, item.symbol, _sm, result.get("technical"), result.get("fundamental"), su, sc,
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


@app.post("/portfolios/{portfolio_id}/analyze/all")
async def analyze_portfolio_all(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    """Analyze only stale holdings (> 60 min). Runs up to 10 concurrently with timeout protection."""
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    items = db.query(PortfolioItem).filter(PortfolioItem.portfolio_id == portfolio_id).all()
    symbols = [i.symbol for i in items]
    cache_map = {
        c.symbol: c
        for c in db.query(AnalysisCache).filter(
            AnalysisCache.workspace_id == ws,
            AnalysisCache.symbol.in_(symbols),
        ).all()
    }
    s   = _get_ai_settings(db, ws)
    src = _get_analysis_sources(db, ws)

    stale_syms   = [sym for sym in symbols if _is_stale_60m(cache_map.get(sym))]
    skipped_syms = [sym for sym in symbols if not _is_stale_60m(cache_map.get(sym))]

    results: list[dict] = []
    if stale_syms:
        results = list(await asyncio.gather(
            *[_analyze_one_concurrent(ws, sym, s, src) for sym in stale_syms]
        ))

    return {
        "total":    len(symbols),
        "analyzed": len(results),
        "skipped":  len(skipped_syms),
        "results":  results,
        "skipped_symbols": skipped_syms,
    }


@app.post("/watchlist/analyze/all")
async def analyze_watchlist_60m(db: Session = Depends(get_db)) -> dict:
    """Analyze only stale watchlist symbols (> 60 min). Runs up to 10 concurrently with timeout protection."""
    ws = _ws_id(db)
    items = db.query(Watchlist).filter(Watchlist.workspace_id == ws).order_by(Watchlist.symbol).all()
    symbols = [i.symbol for i in items]
    cache_map = {
        c.symbol: c
        for c in db.query(AnalysisCache).filter(
            AnalysisCache.workspace_id == ws,
            AnalysisCache.symbol.in_(symbols),
        ).all()
    }
    s   = _get_ai_settings(db, ws)
    src = _get_analysis_sources(db, ws)

    stale_syms   = [sym for sym in symbols if _is_stale_60m(cache_map.get(sym))]
    skipped_syms = [sym for sym in symbols if not _is_stale_60m(cache_map.get(sym))]

    results: list[dict] = []
    if stale_syms:
        results = list(await asyncio.gather(
            *[_analyze_one_concurrent(ws, sym, s, src) for sym in stale_syms]
        ))

    return {
        "total":    len(symbols),
        "analyzed": len(results),
        "skipped":  len(skipped_syms),
        "results":  results,
        "skipped_symbols": skipped_syms,
    }


@app.post("/watchlist/analyze/all/stream")
async def analyze_watchlist_stream(db: Session = Depends(get_db)) -> StreamingResponse:
    """
    Streaming version of watchlist analyze/all.
    Emits newline-delimited JSON events as each stock completes:
      {"type":"start",    "total":N, "stale":M, "skipped":K}
      {"type":"progress", "done":k,  "total":M, "result":{...}}
      {"type":"complete", "total":N, "analyzed":M, "skipped":K, "fallbacks":F}
    """
    ws = _ws_id(db)
    items = db.query(Watchlist).filter(Watchlist.workspace_id == ws).order_by(Watchlist.symbol).all()
    symbols = [i.symbol for i in items]
    cache_map = {
        c.symbol: c
        for c in db.query(AnalysisCache).filter(
            AnalysisCache.workspace_id == ws,
            AnalysisCache.symbol.in_(symbols),
        ).all()
    }
    s   = _get_ai_settings(db, ws)
    src = _get_analysis_sources(db, ws)

    stale_syms   = [sym for sym in symbols if _is_stale_60m(cache_map.get(sym))]
    skipped_syms = [sym for sym in symbols if not _is_stale_60m(cache_map.get(sym))]

    async def generate():
        total_stale = len(stale_syms)
        yield _ndjson({"type": "start", "total": len(symbols), "stale": total_stale, "skipped": len(skipped_syms)})

        if total_stale == 0:
            yield _ndjson({"type": "complete", "total": len(symbols), "analyzed": 0, "skipped": len(skipped_syms), "fallbacks": 0})
            return

        queue: asyncio.Queue = asyncio.Queue()

        async def _work(sym: str) -> None:
            result = await _analyze_one_concurrent(ws, sym, s, src)
            await queue.put(result)

        for sym in stale_syms:
            asyncio.create_task(_work(sym))

        done_count = 0
        fallback_count = 0
        for _ in range(total_stale):
            result = await queue.get()
            done_count += 1
            if result.get("ai_fallback_used"):
                fallback_count += 1
            yield _ndjson({"type": "progress", "done": done_count, "total": total_stale, "result": result})

        yield _ndjson({
            "type":      "complete",
            "total":     len(symbols),
            "analyzed":  done_count,
            "skipped":   len(skipped_syms),
            "fallbacks": fallback_count,
        })

    return StreamingResponse(generate(), media_type="application/x-ndjson")


# ─── Async Job-based Watchlist Analysis ───────────────────────────────────────

@app.post("/analyze/watchlist", status_code=202)
async def start_watchlist_job(background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    """
    Enqueue a watchlist analysis job and return immediately with a job_id.
    Client polls GET /analyze/jobs/{job_id} or streams GET /analyze/jobs/{job_id}/stream.
    """
    _cleanup_jobs()
    ws = _ws_id(db)
    items = db.query(Watchlist).filter(Watchlist.workspace_id == ws).order_by(Watchlist.symbol).all()
    symbols = [i.symbol for i in items]
    cache_map = {
        c.symbol: c
        for c in db.query(AnalysisCache).filter(
            AnalysisCache.workspace_id == ws,
            AnalysisCache.symbol.in_(symbols),
        ).all()
    }
    s   = _get_ai_settings(db, ws)
    src = _get_analysis_sources(db, ws)
    stale_syms = [sym for sym in symbols if _is_stale_60m(cache_map.get(sym))]

    job_id = str(_uuid.uuid4())
    _JOBS[job_id] = {
        "status":     "queued",
        "total":      len(stale_syms),
        "done":       0,
        "fallbacks":  0,
        "results":    [],
        "skipped":    len(symbols) - len(stale_syms),
        "created_at": datetime.utcnow(),
    }
    background_tasks.add_task(_run_analysis_job, job_id, ws, stale_syms, s, src)
    _log.info("[job:%s] queued — %d stale, %d skipped", job_id, len(stale_syms), len(symbols) - len(stale_syms))
    return {
        "job_id": job_id,
        "status": "queued",
        "total":  len(symbols),
        "stale":  len(stale_syms),
    }


@app.get("/analyze/jobs/{job_id}")
async def get_job_status(job_id: str) -> dict:
    """Poll the current state of an analysis job."""
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")
    total = job["total"]
    done  = job["done"]
    return {
        "job_id":       job_id,
        "status":       job["status"],
        "total":        total,
        "done":         done,
        "skipped":      job["skipped"],
        "fallbacks":    job["fallbacks"],
        "progress_pct": round(done / total * 100) if total > 0 else 100,
        "results":      job["results"],
    }


@app.get("/analyze/jobs/{job_id}/stream")
async def stream_job(job_id: str) -> StreamingResponse:
    """
    SSE stream for a running analysis job. Emits:
      data: {"type":"start",    "total":N, "stale":N, "skipped":K}
      data: {"type":"progress", "done":k,  "total":N, "symbol":"...", "signal":"...", "ai_fallback_used":bool}
      data: {"type":"complete", "done":N,  "total":N, "skipped":K, "fallbacks":F}
    """
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    async def generate():
        total   = job["total"]
        skipped = job["skipped"]
        yield f"data: {_json.dumps({'type': 'start', 'total': total, 'stale': total, 'skipped': skipped})}\n\n"

        if total == 0:
            yield f"data: {_json.dumps({'type': 'complete', 'done': 0, 'total': 0, 'skipped': skipped, 'fallbacks': 0})}\n\n"
            return

        idx = 0
        while True:
            results = job["results"]
            while idx < len(results):
                r = results[idx]
                idx += 1
                payload = {
                    "type":            "progress",
                    "done":            idx,
                    "total":           total,
                    "symbol":          r.get("symbol", ""),
                    "signal":          (r.get("summary") or {}).get("signal", ""),
                    "ai_fallback_used": r.get("ai_fallback_used", False),
                }
                yield f"data: {_json.dumps(payload)}\n\n"

            if job["status"] in ("done", "failed"):
                break
            await asyncio.sleep(0.2)

        complete = {
            "type":      "complete",
            "done":      job["done"],
            "total":     total,
            "skipped":   skipped,
            "fallbacks": job["fallbacks"],
        }
        yield f"data: {_json.dumps(complete)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ─── Analysis History ─────────────────────────────────────────────────────────

@app.get("/analysis/history/{symbol}")
async def get_analysis_history(symbol: str, db: Session = Depends(get_db)) -> list[dict]:
    ws = _ws_id(db)
    resolved = _resolve_symbol(symbol)
    rows = (
        db.query(AnalysisHistory)
        .filter(AnalysisHistory.workspace_id == ws, AnalysisHistory.symbol == resolved)
        .order_by(AnalysisHistory.analyzed_at.desc())
        .limit(20)
        .all()
    )
    return [_history_row(r) for r in rows]


@app.delete("/analysis/history/{symbol}/{history_id}")
async def delete_analysis_history_entry(
    symbol: str, history_id: int, db: Session = Depends(get_db)
) -> dict:
    ws = _ws_id(db)
    resolved = _resolve_symbol(symbol)
    row = db.query(AnalysisHistory).filter(
        AnalysisHistory.workspace_id == ws,
        AnalysisHistory.id == history_id,
        AnalysisHistory.symbol == resolved,
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
    ws = _ws_id(db)
    resolved = _resolve_symbol(symbol)
    # Fetch recent rows to find the latest day
    recent = (
        db.query(AnalysisHistory)
        .filter(AnalysisHistory.workspace_id == ws, AnalysisHistory.symbol == resolved)
        .order_by(AnalysisHistory.analyzed_at.desc())
        .limit(20)
        .all()
    )
    if not recent:
        return {"symbol": resolved, "error": "No analysis history found", "breakdown": []}

    # Only keep analyses from the same calendar day as the most recent one (UTC)
    latest_date = recent[0].analyzed_at[:10] if isinstance(recent[0].analyzed_at, str) else recent[0].analyzed_at.strftime("%Y-%m-%d")
    rows = [
        r for r in recent
        if (r.analyzed_at[:10] if isinstance(r.analyzed_at, str) else r.analyzed_at.strftime("%Y-%m-%d")) == latest_date
    ]

    signal_counts: dict[str, int] = {"ACCUMULATE": 0, "BUY": 0, "WATCH": 0, "HOLD": 0, "REDUCE": 0, "SELL": 0}
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
    ws = _ws_id(db)
    resolved = _resolve_symbol(symbol)
    rows = (
        db.query(AnalysisHistory)
        .filter(AnalysisHistory.workspace_id == ws, AnalysisHistory.symbol == resolved)
        .order_by(AnalysisHistory.analyzed_at.desc())
        .limit(5)
        .all()
    )
    if len(rows) < 2:
        return {"error": "Need at least 2 analyses to compare"}

    s = _get_ai_settings(db, ws)
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
    ws = _ws_id(db)
    resolved = _resolve_symbol(symbol)
    src = _get_analysis_sources(db, ws)
    result = await _run_full_analysis_async(db, resolved, body.provider, body.model, src)
    summary = result.get("summary", {})
    su = result.get("sources_used")
    sc = result.get("scores")
    entry = _save_analysis_history(db, ws, resolved, summary, result.get("technical"), result.get("fundamental"), su, sc,
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
    ws = _ws_id(db)
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == body.portfolio_id,
        Portfolio.workspace_id == ws,
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    holdings = db.query(PortfolioItem).filter(PortfolioItem.portfolio_id == body.portfolio_id).all()
    watchlist_items = db.query(Watchlist).filter(Watchlist.workspace_id == ws).all()

    if not holdings:
        raise HTTPException(status_code=400, detail="Portfolio has no holdings to optimize")
    if not watchlist_items:
        raise HTTPException(status_code=400, detail="Watchlist is empty — add candidates first")

    all_symbols = [h.symbol for h in holdings] + [w.symbol for w in watchlist_items]

    cache_map = {
        c.symbol: c
        for c in db.query(AnalysisCache).filter(
            AnalysisCache.workspace_id == ws,
            AnalysisCache.symbol.in_(all_symbols),
        ).all()
    }

    semaphore = asyncio.Semaphore(5)
    opt_src = _get_analysis_sources(db, ws)

    async def _get_scores(symbol: str) -> dict:
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
        price_info = await asyncio.to_thread(fetch_price_info, symbol)
        current_price = price_info.get("current_price")
        target_price  = fa.get("target_price") or price_info.get("target_price")
        dr = is_dr_symbol(symbol)
        parent_sym = normalize_dr_symbol(symbol) if dr else None
        upside_price = current_price
        if dr and parent_sym:
            parent_pi = await asyncio.to_thread(fetch_price_info, parent_sym)
            upside_price = parent_pi.get("current_price") or current_price
        upside_pct: float | None = None
        if target_price and upside_price and upside_price > 0:
            upside_pct = round((target_price - upside_price) / upside_price * 100, 1)
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
            "is_dr":         dr,
            "parent_symbol": parent_sym,
            "upside_reference_price": upside_price if dr else None,
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

    ps = _get_portfolio_settings(db, ws)
    max_stocks = ps["max_stocks"]
    max_sector_pct = ps["max_sector_pct"]
    sector_limits = _get_sector_limits(db, ws)
    portfolio_count = len(portfolio_data)
    max_reached = portfolio_count >= max_stocks
    room = max(0, max_stocks - portfolio_count)

    all_pe = [(sym, d["pe_ratio"]) for sym, d in scores_map.items()
              if d.get("pe_ratio") and d["pe_ratio"] > 0]
    all_pe.sort(key=lambda x: x[1])
    n_pe = len(all_pe)
    pe_pct = {sym: round(rank / n_pe * 100) for rank, (sym, _) in enumerate(all_pe)} if n_pe > 2 else {}
    for sym in scores_map:
        scores_map[sym]["valuation_percentile"] = pe_pct.get(sym)

    layers = _get_optimizer_layers(db, ws)
    if body.provider:
        layers["layer1"]["provider"] = body.provider
    if body.model:
        layers["layer1"]["model"] = body.model
    fallback_cfg = _get_optimizer_fallback(db, ws)
    result = await asyncio.to_thread(
        run_layered_optimizer, portfolio_data, watchlist_data, portfolio.name,
        portfolio_count, max_reached, layers, max_stocks, max_sector_pct, sector_limits,
        portfolio.cash_balance or 0.0,
        fallback_cfg["provider"], fallback_cfg["model"],
    )
    result["portfolio_name"] = portfolio.name
    result["analyzed_at"] = datetime.utcnow().isoformat() + "Z"
    result.setdefault("portfolio_count", portfolio_count)
    result.setdefault("max_reached", max_reached)

    upside_map = {sym: d.get("upside_pct") for sym, d in scores_map.items()}
    for item in result.get("watchlist_ranking", []):
        sym = item.get("symbol")
        if sym and item.get("upside_pct") is None:
            item["upside_pct"] = upside_map.get(sym)

    portfolio_syms = {h.symbol for h in holdings}
    ranking = result.get("watchlist_ranking", [])
    new_stocks = sorted(
        [r for r in ranking if r.get("symbol") not in portfolio_syms],
        key=lambda x: x.get("rank", 999),
    )
    for i, r in enumerate(new_stocks):
        if i >= room:
            r["suggested_allocation_pct"] = 0.0
    total_alloc = sum(r.get("suggested_allocation_pct", 0) for r in ranking)
    if total_alloc > 0:
        scale = 100.0 / total_alloc
        for r in ranking:
            if r.get("suggested_allocation_pct", 0) > 0:
                r["suggested_allocation_pct"] = round(r["suggested_allocation_pct"] * scale, 1)
    result["watchlist_ranking"] = ranking

    entry = OptimizerHistory(
        workspace_id=ws,
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
        optimizer_status=result.get("status", "REBALANCE"),
        rebalance_opportunity_score=result.get("rebalance_opportunity_score"),
        no_action_reason=result.get("no_action_reason"),
        no_action_summary=result.get("no_action_summary"),
        blocked_opportunities_json=_json.dumps(result.get("blocked_opportunities", [])),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    result["history_id"] = entry.id

    # ── Signal History pipeline ────────────────────────────────────────────────
    # Record every actionable allocation confirmed by the Consensus Engine so
    # the data is available for future backtesting and AI tuning.
    _ACTIONABLE = {"BUY", "SELL", "ACCUMULATE", "REDUCE"}
    session_id = str(entry.id)
    ai_provider = result.get("ai_provider")
    ai_model = result.get("ai_model")
    signal_rows: list[SignalHistory] = []

    for alloc in result.get("target_allocations", []):
        action = (alloc.get("action") or "").upper()
        if action not in _ACTIONABLE:
            continue
        sym = alloc.get("symbol", "")
        score_data = scores_map.get(sym, {})
        signal_rows.append(SignalHistory(
            workspace_id=ws,
            session_id=session_id,
            symbol=sym,
            sector=score_data.get("sector"),
            action=action,
            signal=score_data.get("signal", "HOLD"),
            signal_type="L2",
            confidence=result.get("consensus", {}).get("confidence"),
            ta_score=score_data.get("ta_score"),
            fa_score=score_data.get("fa_score"),
            score_at_signal=score_data.get("combined_score"),
            ai_provider=ai_provider,
            ai_model=ai_model,
            price_at_signal=score_data.get("current_price"),
            reasoning_snippet=(alloc.get("reason") or "")[:200],
            recorded_at=datetime.utcnow(),
        ))

    if signal_rows:
        db.add_all(signal_rows)
        db.commit()

    return result


@app.get("/optimizer/history")
async def list_optimizer_history(portfolio_id: int, db: Session = Depends(get_db)) -> list[dict]:
    ws = _ws_id(db)
    rows = (
        db.query(OptimizerHistory)
        .filter(OptimizerHistory.workspace_id == ws, OptimizerHistory.portfolio_id == portfolio_id)
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
            "optimizer_status": r.optimizer_status or "REBALANCE",
            "rebalance_opportunity_score": r.rebalance_opportunity_score,
            "no_action_reason": r.no_action_reason,
        }
        for r in rows
    ]


@app.get("/optimizer/history/{history_id}")
async def get_optimizer_history_detail(history_id: int, db: Session = Depends(get_db)) -> dict:
    ws = _ws_id(db)
    row = db.query(OptimizerHistory).filter(
        OptimizerHistory.workspace_id == ws,
        OptimizerHistory.id == history_id,
    ).first()
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


def _get_sector_limits(db: Session, ws: int) -> dict:
    row = db.query(Settings).filter(
        Settings.workspace_id == ws,
        Settings.key == "sector_limits",
    ).first()
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
    return _get_sector_limits(db, _ws_id(db))


class SectorLimitsBody(BaseModel):
    limits: dict


@app.patch("/settings/sector-limits")
async def update_sector_limits(body: SectorLimitsBody, db: Session = Depends(get_db)) -> dict:
    ws = _ws_id(db)
    current = _get_sector_limits(db, ws)
    for sector, pct in body.limits.items():
        try:
            current[sector] = max(5, min(100, int(pct)))
        except (TypeError, ValueError):
            pass
    _upsert_setting(db, ws, "sector_limits", _json.dumps(current))
    db.commit()
    return current


def _get_portfolio_settings(db: Session, ws: int) -> dict:
    row = db.query(Settings).filter(
        Settings.workspace_id == ws,
        Settings.key == "portfolio_settings",
    ).first()
    if not row:
        return dict(_DEFAULT_PORTFOLIO_SETTINGS)
    try:
        saved = _json.loads(row.value)
        return {k: int(saved.get(k, v)) for k, v in _DEFAULT_PORTFOLIO_SETTINGS.items()}
    except Exception:
        return dict(_DEFAULT_PORTFOLIO_SETTINGS)


@app.get("/settings/portfolio")
async def get_portfolio_settings(db: Session = Depends(get_db)) -> dict:
    return _get_portfolio_settings(db, _ws_id(db))


class PortfolioSettingsBody(BaseModel):
    max_stocks: int | None = None
    max_sector_pct: int | None = None


@app.patch("/settings/portfolio")
async def update_portfolio_settings(body: PortfolioSettingsBody, db: Session = Depends(get_db)) -> dict:
    ws = _ws_id(db)
    current = _get_portfolio_settings(db, ws)
    if body.max_stocks is not None:
        current["max_stocks"] = max(1, min(30, body.max_stocks))
    if body.max_sector_pct is not None:
        current["max_sector_pct"] = max(10, min(100, body.max_sector_pct))
    _upsert_setting(db, ws, "portfolio_settings", _json.dumps(current))
    db.commit()
    return current


def _get_optimizer_layers(db: Session, ws: int) -> dict:
    row = db.query(Settings).filter(
        Settings.workspace_id == ws,
        Settings.key == "optimizer_layers",
    ).first()
    if not row:
        return _DEFAULT_LAYERS
    try:
        saved = _json.loads(row.value)
        return {k: {**_DEFAULT_LAYERS[k], **saved.get(k, {})} for k in ("layer1", "layer2", "layer3")}
    except Exception:
        return _DEFAULT_LAYERS


@app.get("/settings/optimizer-layers")
async def get_optimizer_layers(db: Session = Depends(get_db)) -> dict:
    return _get_optimizer_layers(db, _ws_id(db))


class OptimizerLayerUpdate(BaseModel):
    layer: str
    provider: str
    model: str


@app.patch("/settings/optimizer-layers")
async def update_optimizer_layer(body: OptimizerLayerUpdate, db: Session = Depends(get_db)) -> dict:
    ws = _ws_id(db)
    if body.layer not in ("layer1", "layer2", "layer3"):
        raise HTTPException(status_code=400, detail="Invalid layer name")
    row = db.query(Settings).filter(Settings.workspace_id == ws, Settings.key == "optimizer_layers").first()
    try:
        current = _json.loads(row.value) if row else {}
    except Exception:
        current = {}
    layers = {k: {**_DEFAULT_LAYERS[k], **current.get(k, {})} for k in ("layer1", "layer2", "layer3")}
    layers[body.layer]["provider"] = body.provider
    layers[body.layer]["model"] = body.model
    _upsert_setting(db, ws, "optimizer_layers", _json.dumps(layers))
    db.commit()
    return layers


_DEFAULT_FALLBACK: dict = {"provider": "anthropic", "model": "claude-sonnet-4-6"}


def _get_optimizer_fallback(db: Session, ws: int) -> dict:
    row = db.query(Settings).filter(
        Settings.workspace_id == ws,
        Settings.key == "optimizer_fallback",
    ).first()
    if not row:
        return dict(_DEFAULT_FALLBACK)
    try:
        saved = _json.loads(row.value)
        return {k: saved.get(k, v) for k, v in _DEFAULT_FALLBACK.items()}
    except Exception:
        return dict(_DEFAULT_FALLBACK)


@app.get("/settings/optimizer-fallback")
async def get_optimizer_fallback(db: Session = Depends(get_db)) -> dict:
    return _get_optimizer_fallback(db, _ws_id(db))


class OptimizerFallbackBody(BaseModel):
    provider: str
    model: str


@app.patch("/settings/optimizer-fallback")
async def update_optimizer_fallback(body: OptimizerFallbackBody, db: Session = Depends(get_db)) -> dict:
    ws = _ws_id(db)
    updated = {"provider": body.provider, "model": body.model}
    _upsert_setting(db, ws, "optimizer_fallback", _json.dumps(updated))
    db.commit()
    return updated


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
    """Backfill sector column for existing watchlist and portfolio items that are missing it."""
    import asyncio as _asyncio
    ws = _ws_id(db)

    wl_items = db.query(Watchlist).filter(
        Watchlist.workspace_id == ws,
        (Watchlist.sector == None) | (Watchlist.sector == "Other"),  # noqa: E711
    ).all()
    pi_items = db.query(PortfolioItem).filter(
        PortfolioItem.workspace_id == ws,
        (PortfolioItem.sector == None) | (PortfolioItem.sector == "Other"),  # noqa: E711
    ).all()

    wl_updated = 0
    pi_updated = 0
    failed: list[str] = []
    last_was_live = False

    async def _resolve(symbol: str) -> str:
        nonlocal last_was_live
        sector = _get_sector(symbol, None)
        if sector != "Other":
            last_was_live = False
            return sector
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
    """One-time migration: patch FA agent cache entries with the correct sector field."""
    ws = _ws_id(db)
    portfolio_syms = {i.symbol for i in db.query(PortfolioItem).filter(PortfolioItem.workspace_id == ws).all()}
    watchlist_syms = {i.symbol for i in db.query(Watchlist).filter(Watchlist.workspace_id == ws).all()}
    all_symbols = sorted(portfolio_syms | watchlist_syms)

    fa_rows: dict[str, AgentCache] = {
        row.symbol: row
        for row in db.query(AgentCache).filter(
            AgentCache.symbol.in_(all_symbols), AgentCache.agent == "fundamental"
        ).all()
    }

    results = []
    updated = 0

    for sym in all_symbols:
        fa_data: dict | None = None
        row = fa_rows.get(sym)
        if row:
            try:
                fa_data = _json.loads(row.result_json)
            except Exception:
                fa_data = None

        sector = _get_sector(sym, fa_data)

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
async def get_latency_stats(
    db: Session = Depends(get_db),
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict:
    """Aggregated AI call latency grouped by provider+model (analysis) and provider+model+layer (optimizer)."""
    query = db.query(UserUsage)
    if from_date:
        query = query.filter(UserUsage.created_at >= datetime.fromisoformat(from_date))
    if to_date:
        query = query.filter(UserUsage.created_at < datetime.fromisoformat(to_date) + timedelta(days=1))
    rows = query.all()

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
async def get_cost_estimate(
    db: Session = Depends(get_db),
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict:
    """Token usage and cost estimate grouped by provider+model from UserUsage records."""
    query = db.query(UserUsage)
    if from_date:
        query = query.filter(UserUsage.created_at >= datetime.fromisoformat(from_date))
    if to_date:
        query = query.filter(UserUsage.created_at < datetime.fromisoformat(to_date) + timedelta(days=1))
    rows = query.all()
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
    return _get_ai_settings(db, _ws_id(db))


@app.patch("/settings/ai-models")
async def update_ai_settings(body: AISettingsBody, db: Session = Depends(get_db)) -> dict:
    ws = _ws_id(db)
    for key, value in body.dict(exclude_none=True).items():
        _upsert_setting(db, ws, key, value)
    db.commit()
    return _get_ai_settings(db, ws)


@app.get("/settings/analysis-sources")
async def get_analysis_sources_endpoint(db: Session = Depends(get_db)) -> dict:
    return _get_analysis_sources(db, _ws_id(db))


class AnalysisSourcesBody(BaseModel):
    use_ta:   bool | None = None
    use_fa:   bool | None = None
    use_news: bool | None = None


@app.patch("/settings/analysis-sources")
async def update_analysis_sources(body: AnalysisSourcesBody, db: Session = Depends(get_db)) -> dict:
    ws = _ws_id(db)
    current = _get_analysis_sources(db, ws)
    updates = {k: v for k, v in body.dict().items() if v is not None}
    merged = {**current, **updates}
    _upsert_setting(db, ws, "analysis_sources", _json.dumps(merged))
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
    ws = _ws_id(db)
    symbol = _resolve_symbol(symbol)
    cached = db.query(AnalysisCache).filter(
        AnalysisCache.workspace_id == ws,
        AnalysisCache.symbol == symbol,
    ).first()
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


# ─── Transactions ─────────────────────────────────────────────────────────────

class TransactionBuyBody(BaseModel):
    symbol: str
    shares: float
    price_per_share: float
    fees: float = 0.0
    taxes: float = 0.0
    currency: str = "THB"
    exchange_rate: float = 1.0
    transaction_date: str | None = None
    notes: str | None = None


class TransactionSellBody(BaseModel):
    symbol: str
    shares: float
    price_per_share: float
    fees: float = 0.0
    taxes: float = 0.0
    currency: str = "THB"
    exchange_rate: float = 1.0
    transaction_date: str | None = None
    notes: str | None = None
    remove_if_zero: bool = True


class TransactionDepositBody(BaseModel):
    amount: float
    currency: str = "THB"
    exchange_rate: float = 1.0
    transaction_date: str | None = None
    notes: str | None = None


class TransactionWithdrawBody(BaseModel):
    amount: float
    currency: str = "THB"
    exchange_rate: float = 1.0
    transaction_date: str | None = None
    notes: str | None = None


class TransactionInitialPositionBody(BaseModel):
    symbol: str
    shares: float
    avg_cost: float
    transaction_date: str | None = None
    notes: str | None = None


class TransactionInitialCashBody(BaseModel):
    amount: float
    currency: str = "THB"
    transaction_date: str | None = None
    notes: str | None = None


class TransactionDividendBody(BaseModel):
    symbol: str | None = None
    amount: float
    currency: str = "THB"
    exchange_rate: float = 1.0
    transaction_date: str | None = None
    notes: str | None = None


def _parse_tx_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.rstrip("Z"))
    except ValueError:
        return None


def _tx_row(tx: Transaction) -> dict:
    return {
        "id": tx.id,
        "portfolio_id": tx.portfolio_id,
        "symbol": tx.symbol,
        "type": tx.transaction_type,
        "shares": tx.shares,
        "price_per_share": tx.price_per_share,
        "total_amount": tx.total_amount,
        "fees": tx.fees,
        "taxes": tx.taxes if tx.taxes is not None else 0.0,
        "currency": tx.currency or "THB",
        "exchange_rate": tx.exchange_rate if tx.exchange_rate is not None else 1.0,
        "transaction_date": tx.transaction_date.isoformat() + "Z",
        "notes": tx.notes,
        "sector": tx.sector,
        "created_at": tx.created_at.isoformat() + "Z" if tx.created_at else None,
    }


@app.post("/portfolios/{portfolio_id}/transactions/buy", status_code=201)
async def transaction_buy(
    portfolio_id: int,
    body: TransactionBuyBody,
    db: Session = Depends(get_db),
) -> dict:
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    symbol = _resolve_symbol(body.symbol)

    if body.shares <= 0:
        raise HTTPException(status_code=422, detail="shares must be positive")
    if body.price_per_share <= 0:
        raise HTTPException(status_code=422, detail="price_per_share must be positive")
    if body.fees < 0:
        raise HTTPException(status_code=422, detail="fees cannot be negative")

    tx_date = _parse_tx_date(body.transaction_date)

    # Resolve sector for new holdings (may already exist; service handles both paths)
    sector = await _fetch_sector(symbol)

    result = execute_buy(
        db=db,
        ws_id=ws,
        portfolio_id=portfolio_id,
        symbol=symbol,
        shares=body.shares,
        price_per_share=body.price_per_share,
        fees=body.fees,
        taxes=body.taxes,
        currency=body.currency,
        exchange_rate=body.exchange_rate,
        transaction_date=tx_date,
        notes=body.notes,
        sector=sector,
    )
    return result


@app.post("/portfolios/{portfolio_id}/transactions/sell", status_code=201)
async def transaction_sell(
    portfolio_id: int,
    body: TransactionSellBody,
    db: Session = Depends(get_db),
) -> dict:
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    symbol = _resolve_symbol(body.symbol)

    if body.shares <= 0:
        raise HTTPException(status_code=422, detail="shares must be positive")
    if body.price_per_share <= 0:
        raise HTTPException(status_code=422, detail="price_per_share must be positive")
    if body.fees < 0:
        raise HTTPException(status_code=422, detail="fees cannot be negative")

    tx_date = _parse_tx_date(body.transaction_date)

    try:
        result = execute_sell(
            db=db,
            ws_id=ws,
            portfolio_id=portfolio_id,
            symbol=symbol,
            shares=body.shares,
            price_per_share=body.price_per_share,
            fees=body.fees,
            taxes=body.taxes,
            currency=body.currency,
            exchange_rate=body.exchange_rate,
            transaction_date=tx_date,
            notes=body.notes,
            remove_if_zero=body.remove_if_zero,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return result


@app.get("/portfolios/{portfolio_id}/transactions")
async def list_transactions(
    portfolio_id: int,
    symbol: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[dict]:
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    q = db.query(Transaction).filter(
        Transaction.workspace_id == ws,
        Transaction.portfolio_id == portfolio_id,
    )
    if symbol:
        q = q.filter(Transaction.symbol == _resolve_symbol(symbol))

    txs = q.order_by(Transaction.transaction_date.desc()).limit(min(limit, 500)).all()
    return [_tx_row(tx) for tx in txs]


@app.post("/portfolios/{portfolio_id}/transactions/deposit", status_code=201)
async def transaction_deposit(
    portfolio_id: int,
    body: TransactionDepositBody,
    db: Session = Depends(get_db),
) -> dict:
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if body.amount <= 0:
        raise HTTPException(status_code=422, detail="amount must be positive")

    tx_date = _parse_tx_date(body.transaction_date)
    try:
        return execute_deposit(
            db=db,
            ws_id=ws,
            portfolio_id=portfolio_id,
            amount=body.amount,
            currency=body.currency,
            exchange_rate=body.exchange_rate,
            transaction_date=tx_date,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/portfolios/{portfolio_id}/transactions/withdraw", status_code=201)
async def transaction_withdraw(
    portfolio_id: int,
    body: TransactionWithdrawBody,
    db: Session = Depends(get_db),
) -> dict:
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if body.amount <= 0:
        raise HTTPException(status_code=422, detail="amount must be positive")

    tx_date = _parse_tx_date(body.transaction_date)
    try:
        return execute_withdraw(
            db=db,
            ws_id=ws,
            portfolio_id=portfolio_id,
            amount=body.amount,
            currency=body.currency,
            exchange_rate=body.exchange_rate,
            transaction_date=tx_date,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/portfolios/{portfolio_id}/transactions/initial-position", status_code=201)
async def transaction_initial_position(
    portfolio_id: int,
    body: TransactionInitialPositionBody,
    db: Session = Depends(get_db),
) -> dict:
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if body.shares <= 0:
        raise HTTPException(status_code=422, detail="shares must be positive")
    if body.avg_cost <= 0:
        raise HTTPException(status_code=422, detail="avg_cost must be positive")

    symbol = _resolve_symbol(body.symbol)
    tx_date = _parse_tx_date(body.transaction_date)
    sector = await _fetch_sector(symbol)

    try:
        return execute_initial_position(
            db=db,
            ws_id=ws,
            portfolio_id=portfolio_id,
            symbol=symbol,
            shares=body.shares,
            avg_cost=body.avg_cost,
            transaction_date=tx_date,
            notes=body.notes,
            sector=sector,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/portfolios/{portfolio_id}/transactions/initial-cash", status_code=201)
async def transaction_initial_cash(
    portfolio_id: int,
    body: TransactionInitialCashBody,
    db: Session = Depends(get_db),
) -> dict:
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if body.amount <= 0:
        raise HTTPException(status_code=422, detail="amount must be positive")

    tx_date = _parse_tx_date(body.transaction_date)
    try:
        return execute_initial_cash(
            db=db,
            ws_id=ws,
            portfolio_id=portfolio_id,
            amount=body.amount,
            currency=body.currency,
            transaction_date=tx_date,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/portfolios/{portfolio_id}/transactions/dividend", status_code=201)
async def transaction_dividend(
    portfolio_id: int,
    body: TransactionDividendBody,
    db: Session = Depends(get_db),
) -> dict:
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if body.amount <= 0:
        raise HTTPException(status_code=422, detail="amount must be positive")

    symbol = _resolve_symbol(body.symbol) if body.symbol else None
    tx_date = _parse_tx_date(body.transaction_date)
    try:
        return execute_dividend(
            db=db,
            ws_id=ws,
            portfolio_id=portfolio_id,
            symbol=symbol,
            amount=body.amount,
            currency=body.currency,
            exchange_rate=body.exchange_rate,
            transaction_date=tx_date,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ─── Portfolio Snapshots ───────────────────────────────────────────────────────

class SnapshotGenerateBody(BaseModel):
    portfolio_id: int
    snapshot_date: str | None = None  # "YYYY-MM-DD", defaults to today (UTC)


def _snapshot_row(s: PortfolioSnapshot) -> dict:
    def _parse(raw: str | None):
        if not raw:
            return None
        try:
            return _json.loads(raw)
        except Exception:
            return None

    return {
        "id": s.id,
        "portfolio_id": s.portfolio_id,
        "snapshot_date": s.snapshot_date,
        "total_value": s.total_value,
        "cash_balance": s.cash_balance,
        "total_invested": s.total_invested,
        "unrealized_pnl": s.unrealized_pnl,
        "unrealized_pnl_pct": s.unrealized_pnl_pct,
        "realized_pnl": s.realized_pnl,
        "daily_return_pct": s.daily_return_pct,
        "holdings_count": s.holdings_count,
        "sector_breakdown": _parse(s.sector_breakdown_json),
        "holdings": _parse(s.holdings_json),
        "created_at": s.created_at.isoformat() + "Z" if s.created_at else None,
    }


@app.post("/snapshots/generate", status_code=201)
async def snapshot_generate(
    body: SnapshotGenerateBody,
    db: Session = Depends(get_db),
) -> dict:
    """Generate (or refresh) today's snapshot for the given portfolio.

    Fetches current market prices, computes unrealized/realized P/L, sector
    allocation, and per-holding breakdown, then upserts the PortfolioSnapshot row.
    Safe to call multiple times per day — subsequent calls overwrite the same row.
    """
    ws = _ws_id(db)
    try:
        return await generate_daily_snapshot(
            db=db,
            portfolio_id=body.portfolio_id,
            workspace_id=ws,
            snapshot_date=body.snapshot_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/portfolios/{portfolio_id}/snapshots")
async def list_snapshots(
    portfolio_id: int,
    limit: int = 365,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return historical snapshots for the portfolio, oldest-first (max 365)."""
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    snaps = (
        db.query(PortfolioSnapshot)
        .filter(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.workspace_id == ws,
        )
        .order_by(PortfolioSnapshot.snapshot_date.asc())
        .limit(min(limit, 365))
        .all()
    )
    return [_snapshot_row(s) for s in snaps]


# ─── Signal History ───────────────────────────────────────────────────────────

@app.get("/analytics/signals")
async def get_signal_history(
    symbol: str | None = None,
    action: str | None = None,
    signal_type: str | None = None,
    session_id: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return optimizer-confirmed trade signals ordered by most recent first.

    Query params:
      symbol      — filter to a single symbol
      action      — BUY | SELL | ACCUMULATE | REDUCE
      signal_type — L1 | L2
      session_id  — tie-break to a specific optimizer run (OptimizerHistory.id)
      limit       — max rows returned (default 100, max 500)
    """
    ws = _ws_id(db)
    limit = min(limit, 500)
    q = (
        db.query(SignalHistory)
        .filter(SignalHistory.workspace_id == ws)
    )
    if symbol:
        q = q.filter(SignalHistory.symbol == symbol.upper())
    if action:
        q = q.filter(SignalHistory.action == action.upper())
    if signal_type:
        q = q.filter(SignalHistory.signal_type == signal_type.upper())
    if session_id:
        q = q.filter(SignalHistory.session_id == session_id)
    rows = q.order_by(SignalHistory.recorded_at.desc()).limit(limit).all()
    return [
        {
            "id":               r.id,
            "session_id":       r.session_id,
            "symbol":           r.symbol,
            "sector":           r.sector,
            "action":           r.action,
            "signal":           r.signal,
            "signal_type":      r.signal_type,
            "confidence":       r.confidence,
            "ta_score":         r.ta_score,
            "fa_score":         r.fa_score,
            "score_at_signal":  r.score_at_signal,
            "price_at_signal":  r.price_at_signal,
            "reasoning_snippet": r.reasoning_snippet,
            "ai_provider":      r.ai_provider,
            "ai_model":         r.ai_model,
            "recorded_at":      r.recorded_at.isoformat() + "Z" if r.recorded_at else None,
        }
        for r in rows
    ]


# ─── Performance comparison (benchmark-normalised) ────────────────────────────

@app.get("/analytics/performance-comparison")
async def get_performance_comparison(
    portfolio_id: int,
    benchmarks: str = "^SET.BK,QQQ",
    db: Session = Depends(get_db),
) -> dict:
    """Return portfolio and benchmark performance normalised to base=100.

    Both series start at 100.0 on the portfolio's earliest snapshot date so
    the chart shows relative performance rather than absolute values.

    Query params:
        portfolio_id  — required; the portfolio to compare
        benchmarks    — comma-separated yfinance symbols (default: "^SET,QQQ")

    Response shape (recharts-ready flat array):
        {
          "base_date": "YYYY-MM-DD",
          "portfolio_name": "Main",
          "series": [
            {"key": "portfolio", "label": "Main", "type": "portfolio", "symbol": null},
            {"key": "bm_SET",    "label": "SET Index", "type": "benchmark", "symbol": "^SET"},
            {"key": "bm_QQQ",   "label": "QQQ (NASDAQ-100)", "type": "benchmark", "symbol": "QQQ"},
          ],
          "data": [
            {"date": "2026-05-21", "portfolio": 100.0, "bm_SET": 100.0, "bm_QQQ": 100.0},
            {"date": "2026-05-22", "portfolio": 103.2, "bm_SET": 101.5, "bm_QQQ": null},
          ]
        }
    """
    from services.benchmark_service import bench_key, benchmark_label

    ws = _ws_id(db)

    # Verify portfolio ownership
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.workspace_id == ws,
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Load all portfolio snapshots (oldest first)
    snap_rows = (
        db.query(PortfolioSnapshot)
        .filter(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.workspace_id == ws,
        )
        .order_by(PortfolioSnapshot.snapshot_date.asc())
        .all()
    )
    if not snap_rows:
        return {
            "base_date": None,
            "portfolio_name": portfolio.name,
            "series": [],
            "data": [],
        }

    base_date: str = snap_rows[0].snapshot_date
    portfolio_map: dict[str, float] = {s.snapshot_date: s.total_value for s in snap_rows}
    base_portfolio_value: float = snap_rows[0].total_value

    # Parse requested benchmark symbols
    bench_symbols: list[str] = [s.strip() for s in benchmarks.split(",") if s.strip()]

    # Load benchmark prices for those symbols
    bench_map: dict[str, dict[str, float]] = {sym: {} for sym in bench_symbols}
    bench_base: dict[str, float] = {}

    if bench_symbols:
        bm_rows = (
            db.query(BenchmarkPrice)
            .filter(BenchmarkPrice.symbol.in_(bench_symbols))
            .order_by(BenchmarkPrice.price_date.asc())
            .all()
        )
        for row in bm_rows:
            bench_map[row.symbol][row.price_date] = row.close_price

        # Anchor each benchmark to the closest available price on or after base_date
        for sym in bench_symbols:
            dated = {d: v for d, v in bench_map[sym].items() if d >= base_date}
            if dated:
                anchor_date = min(dated.keys())
                bench_base[sym] = dated[anchor_date]

    # Collect all dates from portfolio + all benchmarks, sorted
    all_dates: set[str] = set(portfolio_map.keys())
    for sym in bench_symbols:
        all_dates.update(d for d in bench_map[sym] if d >= base_date)
    sorted_dates = sorted(all_dates)

    # Build flat recharts data array
    data: list[dict] = []
    for d in sorted_dates:
        row: dict = {"date": d}

        # Portfolio — normalised to base=100
        if d in portfolio_map and base_portfolio_value and base_portfolio_value > 0:
            row["portfolio"] = round(portfolio_map[d] / base_portfolio_value * 100, 4)
        else:
            row["portfolio"] = None

        # Each benchmark — normalised to base=100 from its own anchor price
        for sym in bench_symbols:
            key = bench_key(sym)
            bv = bench_base.get(sym)
            price = bench_map[sym].get(d)
            if price is not None and bv and bv > 0:
                row[key] = round(price / bv * 100, 4)
            else:
                row[key] = None

        data.append(row)

    # Series metadata for the frontend legend / line colours
    series = [
        {"key": "portfolio", "label": portfolio.name, "type": "portfolio", "symbol": None}
    ] + [
        {
            "key": bench_key(sym),
            "label": benchmark_label(sym),
            "type": "benchmark",
            "symbol": sym,
        }
        for sym in bench_symbols
    ]

    return {
        "base_date": base_date,
        "portfolio_name": portfolio.name,
        "series": series,
        "data": data,
    }


@app.post("/admin/benchmark-backfill")
async def admin_benchmark_backfill(
    from_date: str = "2026-05-21",
    to_date: str | None = None,
    symbols: str = "^SET.BK,QQQ",
    db: Session = Depends(get_db),
) -> dict:
    """Backfill historical benchmark prices from yfinance.

    Query params:
        from_date  — start date "YYYY-MM-DD" (default: 2026-05-21)
        to_date    — end date "YYYY-MM-DD" (default: today UTC)
        symbols    — comma-separated yfinance symbols (default: "^SET,QQQ")

    Existing rows are overwritten so stale prices can be corrected.
    """
    from services.benchmark_service import backfill_benchmarks

    sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
    results = await backfill_benchmarks(db, symbols=sym_list, from_date=from_date, to_date=to_date)
    total_rows = sum(r.get("rows", 0) for r in results)
    return {"results": results, "total_rows_written": total_rows}
