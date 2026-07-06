import asyncio
import logging
import random
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, or_ as sa_or

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
    MarketDataCache,
    RecommendationSnapshot, UserExecutionDecision,
    ShadowPortfolio, ShadowPortfolioSnapshot,
    AttributionMetric, ConfidenceCalibrationRecord,
)
from agents.technical import analyze_technical
from agents.fundamental import analyze_fundamental
from agents.news import analyze_news
from agents.summary import analyze_summary, determine_signal
from agents.optimizer import run_optimizer, run_layered_optimizer, _DEFAULT_LAYERS
from services.optimizer.strategy_profiles import (
    STRATEGY_PROFILES, valid_persona,
    compute_style_drift, build_persona_context,
)
from agents.chart_data import fetch_chart_data
from services.data_fetcher import (
    fetch_price_info, fetch_info, normalize_dr_symbol, is_dr_symbol,
    get_cache_stats, calculate_change_percent,
)
from services.scorer import compute_scores
from services.ai_client import call_ai
from services.json_utils import safe_parse_json
from services.portfolio_transactions import (
    execute_buy, execute_sell,
    execute_deposit, execute_withdraw,
    execute_initial_position, execute_initial_cash,
    execute_quantity_correction,
    execute_dividend,
)
from services.portfolio_snapshots import generate_daily_snapshot, SnapshotCoverageError
from services.snapshot_scheduler import setup_scheduler, shutdown_scheduler
from services.analytics.system_health import compute_system_health, compute_ai_reliability
from services.core.runtime_env import get_system_status, is_vps_env, allow_market_fetching
from services.analytics.quant_engine import (
    build_portfolio_metrics, build_benchmark_metrics,
    build_signal_metrics, build_allocation_metrics,
    build_equity_curve, build_rolling_returns, build_sector_evolution,
    get_cached as _analytics_get_cached,
    set_cached as _analytics_set_cached,
    invalidate_cache as _analytics_invalidate,
)
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
    status = get_system_status()
    _log.info(
        "startup: role=%s app_env=%s live_fetch=%s scheduler=%s — %s",
        status["role"],
        status["app_env"],
        status["live_fetch_enabled"],
        status["scheduler_enabled"],
        status["description"],
    )
    setup_scheduler()  # no-op on VPS (guarded inside setup_scheduler)
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
    s = symbol.strip().upper()
    if "." in s:
        return s
    return s


def _normalize_transaction_symbol(symbol: str) -> str:
    """Normalize user-entered transaction symbols.

    Rules:
      1) Trim whitespace
      2) Uppercase
      3) If no suffix and symbol is a known SET ticker, append .BK
      4) Preserve any symbol that already has a suffix (e.g. .BK, .US, etc.)
    """
    s = (symbol or "").strip().upper()
    if not s:
        return s
    if "." in s:
        return s
    if f"{s}.BK" in THAI_SECTOR_MAP:
        return f"{s}.BK"
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
        existing.executive_summary = summary.get("executive_summary") or existing.executive_summary
        existing.ai_summary = summary.get("ai_summary") or existing.ai_summary
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
            executive_summary=summary.get("executive_summary"),
            ai_summary=summary.get("ai_summary"),
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
        executive_summary=summary.get("executive_summary"),
        ai_summary=summary.get("ai_summary"),
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
        "executive_summary": r.executive_summary,
        "ai_summary": r.ai_summary,
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
    "WHA.BK": "Real Estate", "AMATA.BK": "Real Estate",
    # Consumer
    "ICHI.BK": "Consumer", "COM7.BK": "Consumer", "CBG.BK": "Consumer",
    "CPF.BK": "Consumer", "M.BK": "Consumer", "CPAXT.BK": "Consumer",
    "TU.BK": "Consumer", "PLANB.BK": "Consumer",
    # Energy
    "OR.BK": "Energy",
    # Financial
    "KTC.BK": "Financial", "BAM.BK": "Financial", "BLA.BK": "Financial",
    "KGI.BK": "Financial", "ASP.BK": "Financial", "TLI.BK": "Financial",
    # Healthcare
    "MEGA.BK": "Healthcare",
    # Industrial
    "TOA.BK": "Industrial", "STECON.BK": "Industrial", "PREB.BK": "Industrial",
    "SYNTEC.BK": "Industrial", "SCC.BK": "Industrial", "BEM.BK": "Industrial",
    # Technology
    "PIS.BK": "Technology", "CCET.BK": "Technology",
    # Utilities
    "GUNKUL.BK": "Utilities",
}

# Canonical sector keys must match frontend/lib/sectors.ts SECTOR_COLORS
_CANONICAL_SECTORS = frozenset({
    "Technology", "Financial", "Energy", "Healthcare",
    "Consumer", "Industrial", "Real Estate", "Utilities", "Other",
})

# ── DR Sector Master Map ──────────────────────────────────────────────────────
# Authoritative sector for every DR prefix — used instead of yfinance so
# Chinese-listed DRs (SMIC, CATL, BABA) and renamed underlying tickers (MICRON)
# are never left as "Other". Key = letters-only DR prefix (e.g. "NVDA", "MICRON").
_DR_SECTOR_MAP: dict[str, str] = {
    # ── Technology ─────────────────────────────────────────────────────────
    "AAPL":    "Technology",   # Apple
    "NVDA":    "Technology",   # Nvidia
    "MSFT":    "Technology",   # Microsoft
    "GOOGL":   "Technology",   # Alphabet / Google
    "META":    "Technology",   # Meta Platforms
    "AMD":     "Technology",   # Advanced Micro Devices
    "INTEL":   "Technology",   # Intel (DR prefix is full name, not INTC)
    "MICRON":  "Technology",   # Micron Technology (yfinance ticker MU)
    "ASML":    "Technology",   # ASML Holding (semiconductor equipment)
    "ORCL":    "Technology",   # Oracle
    "NFLX":    "Consumer",                 # Netflix (streaming / consumer discretionary)
    "VRT":     "Technology",   # Vertiv (data centre hardware)
    "SMIC":    "Technology",   # Semiconductor Manufacturing Intl Corp
    "BABA":    "Technology",   # Alibaba Group
    "TSM":     "Technology",   # Taiwan Semiconductor (TSMC)
    "QCOM":    "Technology",   # Qualcomm
    # ── Consumer ───────────────────────────────────────────────────────────
    "AMZN":    "Consumer",     # Amazon (Consumer Discretionary)
    "TSLA":    "Consumer",     # Tesla (Consumer Discretionary)
    "ABNB":    "Consumer",     # Airbnb
    # ── Financial ──────────────────────────────────────────────────────────
    "AIA":     "Financial",    # AIA Group (insurance)
    # ── Industrial ─────────────────────────────────────────────────────────
    "CATL":    "Industrial",   # Contemporary Amperex Technology (batteries)
}

_DR_PREFIX_RE = re.compile(r"^([A-Z]+)(\d{2,})$")


def _dr_prefix(symbol: str) -> str | None:
    """Extract the letter prefix from a DR symbol.

    NVDA01.BK → 'NVDA', MICRON01 → 'MICRON', NFLX80.BK → 'NFLX'
    Requires at least 2 trailing digits so Thai single-digit tickers
    (PR9.BK, COM7.BK) are never mistaken for DRs.
    Returns None for non-DR symbols.
    """
    base = symbol.upper().replace(".BK", "")
    m = _DR_PREFIX_RE.match(base)
    return m.group(1) if m else None


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
    """Resolve sector with priority order:
    1. DR stocks  — _DR_SECTOR_MAP (authoritative, no network), then FA cache fallback
    2. Thai .BK   — THAI_SECTOR_MAP first, FA cache as fallback
    3. US stocks  — FA cache (yfinance sector field)
    """
    def _from_cache() -> str | None:
        if fa_cache:
            s = fa_cache.get("sector")
            if s and s not in ("N/A", "Other", ""):
                return normalize_sector(s)
        return None

    base = normalize_dr_symbol(symbol)
    if base != symbol:
        # DR symbol — check master map first (reliable for Chinese DRs etc.)
        prefix = _dr_prefix(symbol)
        if prefix:
            mapped = _DR_SECTOR_MAP.get(prefix)
            if mapped:
                return mapped
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


def _quote_response(price: dict) -> dict:
    """Attach presentation-only day change without writing it to quote cache."""
    return {
        **price,
        "change_percent": calculate_change_percent(
            price.get("current_price"),
            price.get("previous_close"),
        ),
    }


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
    return [{"id": p.id, "name": p.name, "cash_balance": p.cash_balance or 0.0, "goal_target_value": p.goal_target_value, "created_at": p.created_at.isoformat()} for p in items]


@app.post("/portfolios", status_code=201)
async def create_portfolio(body: PortfolioCreate, db: Session = Depends(get_db)) -> dict:
    ws = _ws_id(db)
    p = Portfolio(workspace_id=ws, name=body.name.strip())
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id, "name": p.name, "cash_balance": p.cash_balance or 0.0, "goal_target_value": p.goal_target_value, "created_at": p.created_at.isoformat()}


class CashUpdate(BaseModel):
    cash_balance: float


class GoalUpdate(BaseModel):
    goal_target_value: float | None = Field(default=None, gt=0)  # None clears the goal


@app.patch("/portfolios/{portfolio_id}/goal")
async def update_portfolio_goal(portfolio_id: int, body: GoalUpdate, db: Session = Depends(get_db)) -> dict:
    """Set or clear the portfolio value goal (Phase 4C.1 Operations Center)."""
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    p.goal_target_value = body.goal_target_value
    db.commit()
    return {"id": p.id, "goal_target_value": p.goal_target_value, "ok": True}


# ── Goal Profile (Phase 4C.3 Goal Discovery Wizard) ──────────────────────────

class GoalProfileUpdate(BaseModel):
    """All fields optional — only provided keys are written (partial update).
    Explicit null clears a field. Discovery data only, no projections."""
    goal_type: str | None = None
    goal_priority: str | None = None
    goal_target_date: str | None = None     # YYYY-MM-DD
    risk_personality: str | None = None
    goal_target_value: float | None = Field(default=None, gt=0)


@app.get("/portfolios/{portfolio_id}/goal-profile")
async def get_portfolio_goal_profile(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    """Display-ready goal profile (codes + Thai labels). configured=False until the wizard runs."""
    from services.goal_profile import get_goal_profile
    ws = _ws_id(db)
    profile = get_goal_profile(db, ws, portfolio_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return profile


@app.put("/portfolios/{portfolio_id}/goal-profile")
async def put_portfolio_goal_profile(
    portfolio_id: int, body: GoalProfileUpdate, db: Session = Depends(get_db)
) -> dict:
    """Save Goal Discovery Wizard answers. Partial updates supported; null clears."""
    from services.goal_profile import (
        update_goal_profile, valid_goal_type, valid_goal_priority,
        valid_risk_personality, valid_goal_date,
    )
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    provided = body.model_dump(exclude_unset=True)
    validators = {
        "goal_type": valid_goal_type,
        "goal_priority": valid_goal_priority,
        "goal_target_date": valid_goal_date,
        "risk_personality": valid_risk_personality,
    }
    fields: dict = {}
    for key, raw in provided.items():
        if key == "goal_target_value":
            fields[key] = raw  # gt=0 already enforced by Pydantic
            continue
        if raw is None:
            fields[key] = None  # explicit clear
            continue
        normalized = validators[key](raw)
        if normalized is None:
            raise HTTPException(status_code=422, detail=f"Invalid {key}: {raw!r}")
        fields[key] = normalized
    return update_goal_profile(db, p, fields)


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
    """Return holdings from DB only — no yfinance calls.

    Price fields (current_price, previous_close, change_percent, last_updated, upside_pct) are
    returned as null and filled in by a follow-up call to /prices.
    This makes the endpoint respond in < 500 ms regardless of portfolio size.
    """
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    items = db.query(PortfolioItem).filter(PortfolioItem.portfolio_id == portfolio_id).all()
    if not items:
        return []
    symbols = [item.symbol for item in items]

    # Null prices — filled by /prices endpoint after initial render
    null_prices = [{"current_price": None, "previous_close": None, "change_percent": None, "last_updated": None}
                   for _ in items]

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
    consensus_map = _latest_day_consensus(symbols, ws, db)
    # No parent prices — upside_pct will be null until /prices responds
    return _enrich_holdings(items, null_prices, cached, fa_info, {}, consensus_map)


@app.get("/portfolios/{portfolio_id}/prices")
async def get_portfolio_prices(portfolio_id: int, db: Session = Depends(get_db)) -> list[dict]:
    """Fetch current prices for all holdings (hits MarketDataCache first, 5-min TTL).

    Also returns upside_pct computed server-side (requires FA agent cache + DR parent
    prices) so the frontend can patch all price-dependent columns in one round-trip.
    """
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    items = db.query(PortfolioItem).filter(PortfolioItem.portfolio_id == portfolio_id).all()
    if not items:
        return []
    symbols = [item.symbol for item in items]

    # Parallel price fetch — hits DB cache (5-min TTL) before touching yfinance
    prices = await asyncio.gather(*[asyncio.to_thread(fetch_price_info, item.symbol) for item in items])
    price_map = {item.symbol: pr for item, pr in zip(items, prices)}

    # FA info for target_price + DR detection (DB only, no yfinance)
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

    # DR parent prices needed for upside_pct of DR holdings
    dr_parents = sorted({d["parent_symbol"] for d in fa_info.values() if d.get("is_dr") and d.get("parent_symbol")})
    parent_prices: dict[str, dict] = {}
    if dr_parents:
        pp_list = await asyncio.gather(*[asyncio.to_thread(fetch_price_info, s) for s in dr_parents])
        parent_prices = dict(zip(dr_parents, pp_list))

    result = []
    for item, price in zip(items, prices):
        sym = item.symbol
        info = fa_info.get(sym, {})
        target_price = info.get("target_price")
        is_dr = info.get("is_dr", False)
        parent_sym = info.get("parent_symbol")
        upside_price = (
            (parent_prices.get(parent_sym) or {}).get("current_price")
            if is_dr and parent_sym
            else price.get("current_price")
        )
        upside_pct: float | None = (
            round((target_price - upside_price) / upside_price * 100, 1)
            if target_price and upside_price and upside_price > 0
            else None
        )
        result.append({"symbol": sym, **_quote_response(price), "upside_pct": upside_pct})

    return result


@app.get("/portfolios/{portfolio_id}/sector-breakdown")
async def get_sector_breakdown(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    """Return sector allocation from DB only — no yfinance calls.

    Uses cost basis (avg_cost × shares) as the value proxy so sector weights
    are available instantly.  Sector column is read directly from DB (populated
    at add-time), so this endpoint is pure SQL and responds in < 50 ms.
    """
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    items = db.query(PortfolioItem).filter(PortfolioItem.portfolio_id == portfolio_id).all()
    if not items:
        return {"sectors": [], "total_value": 0}

    sector_limits = _get_sector_limits(db, ws)
    default_limit: int = int(sector_limits.get("default") or _get_portfolio_settings(db, ws).get("max_sector_pct", 40))

    agg: dict[str, dict] = {}
    for item in items:
        mv = item.shares * item.avg_cost  # cost basis — pure DB, no yfinance
        sector = normalize_sector(item.sector)
        if sector not in agg:
            agg[sector] = {"value": 0.0, "stocks": []}
        agg[sector]["value"] += mv
        agg[sector]["stocks"].append(item.symbol)

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


# ─── Strategy Persona endpoints ───────────────────────────────────────────────

@app.get("/strategy-profiles")
async def list_strategy_profiles() -> dict:
    """Return all available strategy persona profiles."""
    return {
        "profiles": [
            {
                "id": k,
                **{f: v for f, v in prof.items() if f != "factor_weights"},
                "factor_weights": prof["factor_weights"],
            }
            for k, prof in STRATEGY_PROFILES.items()
        ]
    }


class PersonaUpdate(BaseModel):
    persona: str


@app.get("/portfolios/{portfolio_id}/persona")
async def get_portfolio_persona(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    """Return the current strategy persona for a portfolio."""
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    persona = valid_persona(p.strategy_persona or "BALANCED")
    from services.optimizer.strategy_profiles import get_profile
    profile = get_profile(persona)
    return {"persona": persona, "profile": profile}


@app.patch("/portfolios/{portfolio_id}/persona")
async def update_portfolio_persona(
    portfolio_id: int, body: PersonaUpdate, db: Session = Depends(get_db)
) -> dict:
    """Assign a strategy persona to a portfolio."""
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    persona = valid_persona(body.persona)
    p.strategy_persona = persona
    db.commit()
    return {"persona": persona, "ok": True}


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

    sector, price = await asyncio.gather(
        _fetch_sector(symbol),
        asyncio.to_thread(fetch_price_info, symbol),
    )

    # Record as INITIAL_POSITION so the snapshot engine can classify this
    # as a non-performance asset inflow and exclude it from return calculations.
    result = execute_initial_position(
        db=db,
        ws_id=ws,
        portfolio_id=portfolio_id,
        symbol=symbol,
        shares=body.shares,
        avg_cost=body.avg_cost,
        sector=sector,
    )

    item = db.query(PortfolioItem).filter_by(portfolio_id=portfolio_id, symbol=symbol).first()
    return {
        "id": item.id,
        "portfolio_id": item.portfolio_id,
        "symbol": item.symbol,
        "shares": item.shares,
        "avg_cost": item.avg_cost,
        **_quote_response(price),
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
            "executive_summary": cache.executive_summary,
            "ai_summary": cache.ai_summary,
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

    import traceback
    async def _worker(sym: str):
        # print("WORKER START", sym)

        try:
            result = await _analyze_one_concurrent(ws, sym, s, src)
            # print("WORKER DONE", sym)
        except Exception:
            traceback.print_exc()
            result = {
                "symbol": sym,
                "error": True,
            }
        finally:
            # print("QUEUE PUT", sym)
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
            # print("ANALYZE", sym, total_latency_ms)
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
            # print(sym, "RETURN")
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

    import time as _time
    if to_run:
        t = _time.perf_counter()
        fresh = await asyncio.gather(*[asyncio.to_thread(fn, symbol) for _, fn in to_run])
        # print(
        #     symbol,
        #     "asyncio.to_thread(fn, symbol)",
        #     round(_time.perf_counter() - t, 3),
        # )
        t = _time.perf_counter()
        for (name, _), result in zip(to_run, fresh):
            _set_agent_cache(db, symbol, name, result)
            if name == "technical":   tech   = result
            elif name == "fundamental": fund = result
            elif name == "news":      news_r = result

        # print(
        #     symbol,
        #     "_set_agent_cache(db, symbol, name, result)",
        #     round(_time.perf_counter() - t, 3),
        # )
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
            "executive_summary": cached.executive_summary,
            "ai_summary": cached.ai_summary,
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
    force_rebalance: bool = False   # bypass all stabilization filters when True


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

    # TEMP DEBUG — cash data-flow trace (2026-07-03), remove after cash_pct bug confirmed
    _log.info(
        "[CASH_TRACE stage=1_DB_FETCH] portfolio_id=%s cash_balance=%.2f holdings_count=%d",
        body.portfolio_id, portfolio.cash_balance or 0.0, len(holdings),
    )

    if not holdings:
        raise HTTPException(status_code=400, detail="Portfolio has no holdings to optimize")
    if not watchlist_items:
        raise HTTPException(status_code=400, detail="Watchlist is empty — add candidates first")

    # Phase 4C.1 — presentation-only run-progress markers (Operations Timeline)
    from functools import partial
    from services.run_progress import start_run, mark_stage, finish_run
    start_run(body.portfolio_id)  # stage: PREPARING_DATA

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

    # ── Phase 4C.6H.2 — Timing enrichment ────────────────────────────────────
    timing_ctx_map: dict = {}
    try:
        from services.optimizer_timing import enrich_scores_with_timing
        timing_ctx_map = await asyncio.to_thread(enrich_scores_with_timing, all_symbols)
        for sym, t in timing_ctx_map.items():
            if sym in scores_map:
                scores_map[sym].update({
                    "timing_score":       t.timing_score,
                    "timing_category":    t.timing_category,
                    "execution_priority": t.execution_priority,
                    "momentum":           t.momentum,
                    "timing_reason":      t.timing_reason,
                })
        _log.info(
            "analyze_optimizer: timing enriched %d/%d symbols",
            len(timing_ctx_map), len(all_symbols),
        )
    except Exception as _tc_err:
        _log.warning("analyze_optimizer: timing enrichment failed — continuing without: %s", _tc_err)

    # ── Phase 3B.10 — Execution quality context ───────────────────────────────
    execution_ctx: dict | None = None
    try:
        from services.optimizer.execution_penalty import (
            compute_portfolio_execution_context,
            apply_execution_score_penalties,
        )
        execution_ctx = compute_portfolio_execution_context(scores_map)
        apply_execution_score_penalties(scores_map, execution_ctx)
        _log.info(
            "analyze_optimizer: execution_ctx — dr_assets=%d high_risk=%d",
            len(execution_ctx.get("dr_symbols", [])),
            len(execution_ctx.get("high_risk_symbols", [])),
        )
    except Exception as _exc_err:
        _log.warning("analyze_optimizer: execution_penalty failed — continuing without: %s", _exc_err)

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

    mark_stage(body.portfolio_id, "ANALYZING_CONTEXT")

    # ── Portfolio DNA + Strategy Persona context ──────────────────────────────
    # Use factor_engine as single source of truth (same engine as DNA page).
    # It's cached for 15 min so this is free when the DNA page was visited first.
    from services.analytics.factor_engine import compute_portfolio_factor_exposure
    persona = valid_persona(portfolio.strategy_persona or "BALANCED")
    fe_result = await asyncio.to_thread(
        compute_portfolio_factor_exposure, db, body.portfolio_id, ws
    )
    portfolio_dna = {
        factor: (
            fe_result.get("factor_exposures", {}).get(factor, {}).get("score") or 50.0
        )
        for factor in ("growth", "value", "momentum", "quality", "dividend")
    }
    drift_data = compute_style_drift(portfolio_dna, persona)
    persona_ctx = build_persona_context(persona, portfolio_dna, drift_data)

    layers = _get_optimizer_layers(db, ws)
    if body.provider:
        layers["layer1"]["provider"] = body.provider
    if body.model:
        layers["layer1"]["model"] = body.model
    fallback_cfg = _get_optimizer_fallback(db, ws)

    # Fetch regime context — graceful degradation if detection fails
    regime_ctx: dict | None = None
    try:
        from services.analytics.regime_detector import detect_regime
        regime_ctx = await asyncio.to_thread(detect_regime, db)
    except Exception as _re:
        _log.warning("analyze_optimizer: regime detection failed — continuing without regime context: %s", _re)

    # ── Phase 3B.5 — Constraint Resolution Layer ─────────────────────────────
    # Merge user preferences + regime policy + emergency + system safety into a
    # single deterministic EffectiveEnvelope before any AI agent is called.
    effective_env: object | None = None
    effective_env_dict: dict | None = None
    try:
        from services.optimizer.constraint_resolver import (
            resolve_constraints as _resolve_constraints,
            envelope_to_dict as _eff_env_to_dict,
        )
        effective_env = _resolve_constraints(ps, sector_limits, regime_ctx, persona_ctx)
        effective_env_dict = _eff_env_to_dict(effective_env)
        _log.info(
            "analyze_optimizer: constraint_resolver ran — %d adjustment(s), emergency=%s",
            len(effective_env.resolver_notes), effective_env.emergency_active,
        )
    except Exception as _cre:
        _log.warning("analyze_optimizer: constraint_resolver failed — continuing without: %s", _cre)

    # ── Phase 3B.4 — Build unified Policy Envelope ────────────────────────────
    policy_ctx: dict | None = None
    try:
        from services.optimizer.policy_engine import compute_policy, envelope_to_dict as _env_to_dict
        from agents.optimizer import _compute_portfolio_weights
        # compute_policy needs holdings enriched with weight_pct (market-value based)
        pd_with_weights = _compute_portfolio_weights(portfolio_data)
        _policy_env = compute_policy(
            persona_ctx, regime_ctx, pd_with_weights,
            consensus=None, max_sector_pct=max_sector_pct,
            effective_envelope=effective_env,
        )
        policy_ctx = _env_to_dict(_policy_env)
    except Exception as _pe:
        _log.error(
            "[POLICY_ENGINE] compute_policy failed — falling back to regime-only mode: %s", _pe,
            exc_info=True,
        )

    result = await asyncio.to_thread(
        run_layered_optimizer, portfolio_data, watchlist_data, portfolio.name,
        portfolio_count, max_reached, layers, max_stocks, max_sector_pct, sector_limits,
        portfolio.cash_balance or 0.0,
        fallback_cfg["provider"], fallback_cfg["model"],
        persona_ctx, regime_ctx, policy_ctx,
        effective_env,
        execution_ctx,
        on_stage=partial(mark_stage, body.portfolio_id),
    )

    # Surface regime in optimizer result for frontend display
    if regime_ctx:
        result["market_regime"] = {
            "regime":               regime_ctx.get("regime"),
            "confidence_pct":       regime_ctx.get("confidence_pct"),
            "trend_score":          regime_ctx.get("trend_score"),
            "volatility_score":     regime_ctx.get("volatility_score"),
            "transition_stability": regime_ctx.get("transition_stability"),
            "regime_duration_days": regime_ctx.get("regime_duration_days"),
            "narrative":            regime_ctx.get("narrative"),
            "transition_warnings":  regime_ctx.get("transition_warnings", []),
        }
    result["portfolio_name"] = portfolio.name
    result["analyzed_at"] = datetime.utcnow().isoformat() + "Z"
    # Health indicator: makes a silently-degraded policy engine visible in AI Analytics
    result["policy_engine_status"] = "ACTIVE" if policy_ctx else "DISABLED_FALLBACK"
    result.setdefault("portfolio_count", portfolio_count)
    result.setdefault("max_reached", max_reached)
    if execution_ctx:
        result["execution_context"] = execution_ctx

    # ── Phase 4C.6H.5 — Enrich target_allocations with timing data ───────────
    if timing_ctx_map:
        from services.optimizer_timing import apply_timing_confidence_adjustment, build_timing_note
        for alloc in result.get("target_allocations", []):
            sym = alloc.get("symbol", "")
            tc = timing_ctx_map.get(sym)
            if tc:
                alloc["timing_score"] = tc.timing_score
                alloc["execution_priority"] = tc.execution_priority
                alloc["timing_note"] = build_timing_note(
                    alloc.get("action", "HOLD"), tc.timing_score, tc.execution_priority
                )
                if alloc.get("confidence") is not None:
                    alloc["confidence"] = apply_timing_confidence_adjustment(
                        float(alloc["confidence"]), tc.timing_score
                    )

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

    mark_stage(body.portfolio_id, "STABILIZING")

    # ── Stabilization Layer ────────────────────────────────────────────────────
    # Applies deterministic post-processing to suppress optimizer hyperactivity:
    # drift threshold buffer, cooldown engine, NO_REBALANCE_REQUIRED state,
    # minimum impact filter, and duplicate ticker diagnostics.
    try:
        from services.optimizer.stabilization import apply_stabilization

        # Find the last REBALANCE run for this portfolio to compute cooldown
        _last_rebalance: datetime | None = None
        _prev_regime: str | None = None
        _last_rebalance_row = (
            db.query(OptimizerHistory)
            .filter(
                OptimizerHistory.portfolio_id == body.portfolio_id,
                OptimizerHistory.workspace_id == ws,
                OptimizerHistory.optimizer_status == "REBALANCE",
            )
            .order_by(OptimizerHistory.analyzed_at.desc())
            .first()
        )
        if _last_rebalance_row:
            _last_rebalance = _last_rebalance_row.analyzed_at
            # Extract previous regime from stored result JSON for regime-change detection
            try:
                _prev_result = _json.loads(_last_rebalance_row.result_json or "{}")
                _prev_regime = (_prev_result.get("market_regime") or {}).get("regime")
            except Exception:
                pass

        result = apply_stabilization(
            result,
            last_rebalance_at=_last_rebalance,
            prev_regime=_prev_regime,
            force_rebalance=body.force_rebalance,
        )
        _log.info(
            "analyze_optimizer: stabilization=%s original_status=%s cooldown_days_remaining=%d",
            result.get("stabilization", {}).get("status", "?"),
            result.get("stabilization", {}).get("original_optimizer_status", "?"),
            result.get("stabilization", {}).get("cooldown", {}).get("days_remaining", 0),
        )
    except Exception as _stab_exc:
        _log.warning("analyze_optimizer: stabilization layer failed — continuing without: %s", _stab_exc)

    mark_stage(body.portfolio_id, "SAVING")

    consensus_block = result.get("consensus") if isinstance(result.get("consensus"), dict) else {}
    result["final_consensus_score"] = consensus_block.get("consensus_strength_score")

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

    # ── Phase 3B.7 — Decision Memory: write RecommendationSnapshot ───────────
    # Persisted automatically after every successful optimizer run.
    # Failure is swallowed — never blocks the HTTP response.
    _snap_id: int | None = None
    try:
        from services.decision_memory.snapshot_writer import write_recommendation_snapshot
        total_mv = sum(
            (h.get("shares") or 0) * (h.get("current_price") or h.get("avg_cost") or 0)
            for h in portfolio_data
        )
        _snap_id = write_recommendation_snapshot(
            db,
            workspace_id=ws,
            portfolio_id=body.portfolio_id,
            optimizer_history_id=entry.id,
            optimizer_result=result,
            persona=persona,
            total_portfolio_value=total_mv,
            scores_map=scores_map,
        )
        if _snap_id:
            result["recommendation_snapshot_id"] = _snap_id
    except Exception as _dm_exc:
        _log.warning("analyze_optimizer: decision_memory snapshot write failed: %s", _dm_exc)

    # ── Phase 3B.7 — Auto-create/refresh ACTIVE_MODEL shadow after every optimizer run ─
    # Ensures attribution metrics accumulate even before a user records an
    # explicit APPROVED decision.  Runs in a background thread — never blocks
    # the HTTP response.  Failure is logged but swallowed.
    if _snap_id:
        def _create_active_model_shadow_bg(
            _portfolio_id: int, _snap_id: int, _workspace_id: int
        ) -> None:
            try:
                from services.decision_memory.shadow_tracker import (
                    create_active_model_shadow, value_shadow_portfolio,
                )
                _bg_db = SessionLocal()
                try:
                    r = create_active_model_shadow(_bg_db, _portfolio_id, _snap_id, _workspace_id)
                    shadow_id = r.get("shadow_id")
                    if shadow_id:
                        value_shadow_portfolio(_bg_db, int(shadow_id))
                        _log.info(
                            "analyze_optimizer: ACTIVE_MODEL shadow id=%s %s for portfolio_id=%s",
                            shadow_id, r.get("action", "ready"), _portfolio_id,
                        )
                finally:
                    _bg_db.close()
            except Exception as _shadow_exc:
                _log.warning(
                    "analyze_optimizer: ACTIVE_MODEL shadow creation failed: %s", _shadow_exc
                )

        import threading as _threading
        _threading.Thread(
            target=_create_active_model_shadow_bg,
            args=(body.portfolio_id, _snap_id, ws),
            daemon=True,
        ).start()

        # ── AI Evaluation M1 (P2) — recommendation-keyed counterfactual shadow ─
        # Every recommendation gets its own frozen-at-inception shadow regardless
        # of what the human later decides, so the Horizon Grading Engine can
        # grade recommendation quality independent of execution behavior.
        def _create_recommendation_shadow_bg(_snap_id: int, _workspace_id: int) -> None:
            try:
                from services.decision_memory.shadow_tracker import create_recommendation_shadow
                _bg_db = SessionLocal()
                try:
                    r = create_recommendation_shadow(_bg_db, _snap_id, _workspace_id)
                    _log.info(
                        "analyze_optimizer: recommendation shadow %s for snapshot_id=%s",
                        r.get("action") or r.get("error"), _snap_id,
                    )
                finally:
                    _bg_db.close()
            except Exception as _rec_shadow_exc:
                _log.warning(
                    "analyze_optimizer: recommendation shadow creation failed: %s", _rec_shadow_exc
                )

        _threading.Thread(
            target=_create_recommendation_shadow_bg,
            args=(_snap_id, ws),
            daemon=True,
        ).start()

        # ── AI Evaluation M2 — day-0 PLAN grade ──────────────────────────────
        # Graded immediately (not on the daily scheduler like horizon grades)
        # since a plan grade needs no maturity window — it scores the plan as
        # it exists at snapshot time. grade_pending_plans() is idempotent
        # (skips snapshots that already have a PLAN row) and re-derives
        # everything from this same snapshot, so this is a pure re-graded-once
        # background write, never a duplicate.
        def _grade_plan_bg(_portfolio_id: int) -> None:
            try:
                from services.evaluation.plan_grader import grade_pending_plans
                _bg_db = SessionLocal()
                try:
                    r = grade_pending_plans(_bg_db, portfolio_id=_portfolio_id)
                    _log.info(
                        "analyze_optimizer: PLAN grading graded=%d skipped=%d for portfolio_id=%s",
                        len(r.get("graded", [])), len(r.get("skipped", [])), _portfolio_id,
                    )
                finally:
                    _bg_db.close()
            except Exception as _plan_grade_exc:
                _log.warning("analyze_optimizer: PLAN grading failed: %s", _plan_grade_exc)

        _threading.Thread(
            target=_grade_plan_bg,
            args=(body.portfolio_id,),
            daemon=True,
        ).start()

    # ── Phase 3B.7 — Confidence calibration: update after every optimizer run ─
    # Runs in a background thread so it never delays the HTTP response.
    # Captures a new ConfidenceCalibrationRecord linking back to this run.
    def _run_calibration_bg(workspace_id: int, oh_id: int, snap_id: int | None) -> None:
        try:
            from services.decision_memory.calibration import compute_calibration
            _bg_db = SessionLocal()
            try:
                compute_calibration(
                    _bg_db,
                    workspace_id=workspace_id,
                    lookback_days=30,
                    optimizer_history_id=oh_id,
                    recommendation_snapshot_id=snap_id,
                )
            finally:
                _bg_db.close()
        except Exception as _cal_exc:
            _log.debug("analyze_optimizer: background calibration failed: %s", _cal_exc)

    import threading
    threading.Thread(
        target=_run_calibration_bg,
        args=(ws, entry.id, _snap_id),
        daemon=True,
    ).start()

    # ── Presentation layer: noise filter ─────────────────────────────────────────
    # Suppresses micro-rebalance BUY/SELL recommendations for the HTTP response
    # only. DB records (history, signal history, snapshots) already saved above
    # with unfiltered optimizer output.
    try:
        from services.noise_filter import apply_noise_filter
        apply_noise_filter(result)
    except Exception as _nf_exc:
        _log.warning("analyze_optimizer: noise filter failed — continuing: %s", _nf_exc)

    # ── UX.2C — Action Summary (deterministic, no AI, no DB) ──────────────────
    try:
        from services.optimizer_action_summary import build_action_summary
        result["action_summary"] = build_action_summary(result.get("target_allocations", []))
    except Exception as _as_exc:
        _log.warning("analyze_optimizer: action_summary failed — continuing: %s", _as_exc)

    # ── Execution Optimization — deterministic post-processing stage ─────────
    # See OPTIMIZER_PHILOSOPHY.md §7/§9/§10. Never re-runs L1/L2/L3, never
    # mutates target_allocations — a response-time view, same pattern as
    # action_summary above.
    try:
        from services.optimizer.execution_optimizer import optimize_execution
        _violations = (result.get("active_policy") or {}).get("violations", [])
        result["execution_optimization"] = optimize_execution(
            result.get("action_summary", {}),
            result.get("target_allocations", []),
            cash_available=float(result.get("cash_balance") or 0.0),
            violations=_violations,
        ).model_dump()
    except Exception as _eo_exc:
        _log.warning("analyze_optimizer: execution_optimization failed — continuing: %s", _eo_exc)

    finish_run(body.portfolio_id, ok=True)
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
    result: list[dict] = []
    for r in rows:
        final_consensus_score = None
        try:
            payload = _json.loads(r.result_json) if r.result_json else {}
            consensus = payload.get("consensus") if isinstance(payload.get("consensus"), dict) else {}
            final_consensus_score = consensus.get("consensus_strength_score")
        except Exception:
            final_consensus_score = None

        result.append({
            "id": r.id,
            "portfolio_name": r.portfolio_name,
            "analyzed_at": r.analyzed_at.isoformat() + "Z",
            "swap_count": r.swap_count,
            "optimizer_status": r.optimizer_status or "REBALANCE",
            "rebalance_opportunity_score": r.rebalance_opportunity_score,
            "final_consensus_score": final_consensus_score,
            "no_action_reason": r.no_action_reason,
        })
    return result


@app.get("/optimizer/history/{history_id}")
async def get_optimizer_history_detail(history_id: int, db: Session = Depends(get_db)) -> dict:
    ws = _ws_id(db)
    row = db.query(OptimizerHistory).filter(
        OptimizerHistory.workspace_id == ws,
        OptimizerHistory.id == history_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="History not found")
    payload = _json.loads(row.result_json)
    if "final_consensus_score" not in payload:
        consensus = payload.get("consensus") if isinstance(payload.get("consensus"), dict) else {}
        payload["final_consensus_score"] = consensus.get("consensus_strength_score")
    # recommendation_snapshot_id is injected into result after result_json is committed,
    # so it is absent from stored history rows. Look it up and inject it here.
    if not payload.get("recommendation_snapshot_id"):
        snap = db.query(RecommendationSnapshot).filter_by(
            optimizer_history_id=history_id,
            workspace_id=ws,
        ).first()
        if snap:
            payload["recommendation_snapshot_id"] = snap.id
    # Noise filter + action_summary are response-time views, applied after
    # result_json is committed — stored rows carry neither. Recompute them here
    # (display-only, row untouched) so history views render the same Execution
    # Plan as live runs. Filter thresholds are current-day, not run-day.
    if "action_summary" not in payload:
        try:
            from services.noise_filter import apply_noise_filter
            from services.optimizer_action_summary import build_action_summary
            apply_noise_filter(payload)
            payload["action_summary"] = build_action_summary(payload.get("target_allocations", []))
        except Exception as _as_exc:
            _log.warning("get_optimizer_history_detail: action_summary backfill failed — continuing: %s", _as_exc)
    if "execution_optimization" not in payload:
        try:
            from services.optimizer.execution_optimizer import optimize_execution
            _violations = (payload.get("active_policy") or {}).get("violations", [])
            payload["execution_optimization"] = optimize_execution(
                payload.get("action_summary", {}),
                payload.get("target_allocations", []),
                cash_available=float(payload.get("cash_balance") or 0.0),
                violations=_violations,
            ).model_dump()
        except Exception as _eo_exc:
            _log.warning("get_optimizer_history_detail: execution_optimization backfill failed — continuing: %s", _eo_exc)
    return payload


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


# AI Evaluation & Execution Intelligence — Milestone M0 (P7: config home for
# evaluation thresholds; see docs/AI_EVALUATION_IMPLEMENTATION_PLAN.md §3).
# Read through this settings service like every other config surface in the
# app — services/evaluation/ must never hardcode these values (ENGINEERING_
# PRINCIPLES.md "Configuration").
_DEFAULT_EVALUATION_SETTINGS: dict = {
    "horizons_days": [7, 30, 90, 180],
    "min_n_letter_grade": 8,
    "min_n_win_rate": 5,
    "tie_band_pct": 0.3,
    "expiry_days": 14,
}


def _get_evaluation_settings(db: Session, ws: int) -> dict:
    row = db.query(Settings).filter(
        Settings.workspace_id == ws,
        Settings.key == "evaluation_settings",
    ).first()
    if not row:
        return dict(_DEFAULT_EVALUATION_SETTINGS)
    try:
        saved = _json.loads(row.value)
        result = dict(_DEFAULT_EVALUATION_SETTINGS)
        result.update({k: saved[k] for k in _DEFAULT_EVALUATION_SETTINGS if k in saved})
        return result
    except Exception:
        return dict(_DEFAULT_EVALUATION_SETTINGS)


@app.get("/settings/evaluation")
async def get_evaluation_settings(db: Session = Depends(get_db)) -> dict:
    return _get_evaluation_settings(db, _ws_id(db))


class EvaluationSettingsBody(BaseModel):
    horizons_days: list[int] | None = None
    min_n_letter_grade: int | None = None
    min_n_win_rate: int | None = None
    tie_band_pct: float | None = None
    expiry_days: int | None = None


@app.patch("/settings/evaluation")
async def update_evaluation_settings(body: EvaluationSettingsBody, db: Session = Depends(get_db)) -> dict:
    ws = _ws_id(db)
    current = _get_evaluation_settings(db, ws)
    if body.horizons_days is not None:
        cleaned = sorted({int(d) for d in body.horizons_days if int(d) > 0})
        if cleaned:
            current["horizons_days"] = cleaned
    if body.min_n_letter_grade is not None:
        current["min_n_letter_grade"] = max(1, body.min_n_letter_grade)
    if body.min_n_win_rate is not None:
        current["min_n_win_rate"] = max(1, body.min_n_win_rate)
    if body.tie_band_pct is not None:
        current["tie_band_pct"] = max(0.0, min(10.0, body.tie_band_pct))
    if body.expiry_days is not None:
        current["expiry_days"] = max(1, body.expiry_days)
    _upsert_setting(db, ws, "evaluation_settings", _json.dumps(current))
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


@app.post("/admin/fix-dr-sectors")
async def fix_dr_sectors(db: Session = Depends(get_db)) -> dict:
    """Apply _DR_SECTOR_MAP to every DR holding in portfolio and watchlist.

    Corrects:
      - sector='Other'  (yfinance returned nothing / Chinese DR)
      - non-canonical values ('Automobile', 'Communication Services', …)
      - inconsistencies (same DR stored with different sectors in different portfolios)

    Also applies THAI_SECTOR_MAP corrections for Thai stocks with non-canonical sectors.
    Safe to run multiple times — idempotent.
    """
    ws = _ws_id(db)

    all_pi = db.query(PortfolioItem).filter(PortfolioItem.workspace_id == ws).all()
    all_wl = db.query(Watchlist).filter(Watchlist.workspace_id == ws).all()

    changes: list[dict] = []
    unmapped: list[dict] = []

    def _correct_sector(symbol: str, current: str | None) -> str | None:
        """Return the correct canonical sector, or None if no correction needed."""
        prefix = _dr_prefix(symbol)
        if prefix is not None:
            # DR symbol — always use master map
            correct = _DR_SECTOR_MAP.get(prefix)
            if correct is None:
                unmapped.append({"symbol": symbol, "prefix": prefix, "current": current})
                return None
            return correct if correct != current else None

        # Thai SET stock — fix if THAI_SECTOR_MAP has an entry that differs
        if symbol.endswith(".BK"):
            correct = THAI_SECTOR_MAP.get(symbol)
            if correct and correct != current:
                return correct
            # Normalise non-canonical values that slipped through
            if current and current not in _CANONICAL_SECTORS:
                normalized = normalize_sector(current)
                if normalized != current:
                    return normalized
        return None

    for item in all_pi:
        table = "portfolio"
        correction = _correct_sector(item.symbol, item.sector)
        if correction is not None:
            changes.append({
                "table": table, "symbol": item.symbol,
                "from": item.sector, "to": correction,
            })
            item.sector = correction

    for item in all_wl:
        table = "watchlist"
        correction = _correct_sector(item.symbol, item.sector)
        if correction is not None:
            changes.append({
                "table": table, "symbol": item.symbol,
                "from": item.sector, "to": correction,
            })
            item.sector = correction

    if changes:
        db.commit()

    return {
        "total_changed": len(changes),
        "changes":  changes,
        "unmapped": unmapped,
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


@app.get("/system/status")
async def system_status():
    """Return the current runtime environment role and feature flags.

    No auth required — used by the frontend to show the Cloud Dashboard badge.
    """
    return get_system_status()


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
        item["estimated_cost_thb"] = round(item["estimated_cost_usd"] * _USD_TO_THB, 4)

    total_usd = round(sum(r["estimated_cost_usd"] for r in result_list), 6)

    return {
        "fx": {"usd_to_thb": _USD_TO_THB},
        "by_model": result_list,
        "total_estimated_usd": total_usd,
        "total_estimated_thb": round(total_usd * _USD_TO_THB, 4),
    }


def _filtered_usage_query(db: Session, from_date: str | None, to_date: str | None):
    query = db.query(UserUsage)
    if from_date:
        query = query.filter(UserUsage.created_at >= datetime.fromisoformat(from_date))
    if to_date:
        query = query.filter(UserUsage.created_at < datetime.fromisoformat(to_date) + timedelta(days=1))
    return query


@app.get("/stats/ai-analytics")
async def get_ai_analytics(
    db: Session = Depends(get_db),
    from_date: str | None = None,
    to_date: str | None = None,
    recent_limit: int = 100,
) -> dict:
    """Unified telemetry for the AI Analytics dashboard: per-model leaderboard, layer
    heatmap, daily cost/latency/token breakdown, and a recent-calls log — all aggregated
    read-only from UserUsage. Reliability fields that aren't tracked yet (success/error,
    JSON parse, timeouts, max-token-stops) are returned as null; fallback_rate is real,
    derived from layer == "fallback"."""
    rows = _filtered_usage_query(db, from_date, to_date).order_by(UserUsage.created_at.asc()).all()

    def _p95(vals: list[int]) -> int:
        if not vals:
            return 0
        sv = sorted(vals)
        return sv[min(int(len(sv) * 0.95), len(sv) - 1)]

    def _avg(vals: list[int]) -> int | None:
        return round(sum(vals) / len(vals)) if vals else None

    model_groups: dict[tuple, dict] = {}
    layer_groups: dict[tuple, dict] = {}
    daily_groups: dict[tuple, dict] = {}

    for row in rows:
        mk = (row.provider, row.model)
        mg = model_groups.setdefault(mk, {
            "provider": row.provider, "model": row.model,
            "call_count": 0, "latencies": [], "cost_total": 0.0,
            "tokens_total": 0, "last_used": None,
            "fallback_calls": 0, "optimize_calls": 0,
        })
        mg["call_count"] += 1
        if row.latency_ms is not None:
            mg["latencies"].append(row.latency_ms)
        mg["cost_total"] += row.total_cost_usd
        mg["tokens_total"] += row.total_tokens
        if row.created_at and (mg["last_used"] is None or row.created_at.isoformat() > mg["last_used"]):
            mg["last_used"] = row.created_at.isoformat() + "Z"
        if row.operation == "optimize":
            mg["optimize_calls"] += 1
            if row.layer == "fallback":
                mg["fallback_calls"] += 1

        lk = (row.provider, row.model, row.layer or "-", row.operation)
        lg = layer_groups.setdefault(lk, {
            "provider": row.provider, "model": row.model, "layer": row.layer or "-",
            "operation": row.operation, "call_count": 0, "latencies": [],
            "cost_total": 0.0, "tokens_total": 0,
        })
        lg["call_count"] += 1
        if row.latency_ms is not None:
            lg["latencies"].append(row.latency_ms)
        lg["cost_total"] += row.total_cost_usd
        lg["tokens_total"] += row.total_tokens

        day = row.created_at.date().isoformat() if row.created_at else "unknown"
        dk = (day, row.provider, row.model, row.layer or "-", row.operation)
        dg = daily_groups.setdefault(dk, {
            "day": day, "provider": row.provider, "model": row.model,
            "layer": row.layer or "-", "operation": row.operation,
            "call_count": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
            "cost_usd": 0.0, "latencies": [],
        })
        dg["call_count"] += 1
        dg["input_tokens"] += row.input_tokens
        dg["output_tokens"] += row.output_tokens
        dg["total_tokens"] += row.total_tokens
        dg["cost_usd"] += row.total_cost_usd
        if row.latency_ms is not None:
            dg["latencies"].append(row.latency_ms)

    leaderboard = [
        {
            "provider": provider, "model": model, "call_count": g["call_count"],
            "avg_latency_ms": _avg(g["latencies"]),
            "p95_latency_ms": _p95(g["latencies"]) if g["latencies"] else None,
            "avg_cost_usd": round(g["cost_total"] / g["call_count"], 6),
            "total_cost_usd": round(g["cost_total"], 6),
            "avg_total_tokens": round(g["tokens_total"] / g["call_count"]),
            "fallback_rate": round(g["fallback_calls"] / g["optimize_calls"], 4) if g["optimize_calls"] else None,
            "success_rate": None,
            "json_parse_success_rate": None,
            "last_used": g["last_used"],
        }
        for (provider, model), g in sorted(model_groups.items(), key=lambda x: -x[1]["call_count"])
    ]

    layer_matrix = [
        {
            "provider": provider, "model": model, "layer": layer, "operation": operation,
            "call_count": g["call_count"],
            "avg_latency_ms": _avg(g["latencies"]),
            "avg_cost_usd": round(g["cost_total"] / g["call_count"], 6),
            "avg_total_tokens": round(g["tokens_total"] / g["call_count"]),
        }
        for (provider, model, layer, operation), g in layer_groups.items()
    ]

    daily = sorted(
        [
            {
                "day": g["day"], "provider": g["provider"], "model": g["model"],
                "layer": g["layer"], "operation": g["operation"], "call_count": g["call_count"],
                "input_tokens": g["input_tokens"], "output_tokens": g["output_tokens"],
                "total_tokens": g["total_tokens"], "cost_usd": round(g["cost_usd"], 6),
                "avg_latency_ms": _avg(g["latencies"]),
                "p95_latency_ms": _p95(g["latencies"]) if g["latencies"] else None,
            }
            for g in daily_groups.values()
        ],
        key=lambda x: x["day"],
    )

    recent_rows = (
        _filtered_usage_query(db, from_date, to_date)
        .order_by(UserUsage.created_at.desc())
        .limit(max(1, min(recent_limit, 500)))
        .all()
    )
    recent = [
        {
            "id": r.id,
            "created_at": (r.created_at.isoformat() + "Z") if r.created_at else None,
            "provider": r.provider, "model": r.model, "operation": r.operation,
            "layer": r.layer, "latency_ms": r.latency_ms,
            "input_tokens": r.input_tokens, "output_tokens": r.output_tokens,
            "total_tokens": r.total_tokens, "cost_usd": round(r.total_cost_usd, 6),
            "status": "success",  # UserUsage only ever records completed calls today
        }
        for r in recent_rows
    ]

    total_cost = round(sum(r.total_cost_usd for r in rows), 6)

    return {
        "fx": {"usd_to_thb": _USD_TO_THB},
        "leaderboard": leaderboard,
        "layer_matrix": layer_matrix,
        "daily": daily,
        "recent": recent,
        "reliability": compute_ai_reliability(db),
        "totals": {
            "call_count": len(rows),
            "total_cost_usd": total_cost,
            "total_cost_thb": round(total_cost * _USD_TO_THB, 4),
            "total_tokens": sum(r.total_tokens for r in rows),
        },
    }


@app.get("/stats/system-health")
async def get_system_health(db: Session = Depends(get_db)) -> dict:
    """Read-only operational health snapshot for AI providers, the optimizer
    pipeline, the Policy Engine, market data freshness, the portfolio/snapshot
    engine, and background jobs. Every field is a direct read or trivial
    aggregate of existing data (see services/analytics/system_health.py) —
    no health-level thresholds are computed here; the frontend applies a
    single shared healthy/warning/problem/unknown model to every card."""
    return compute_system_health(db, _ws_id(db))


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
    currency: str = "THB"
    exchange_rate: float = 1.0
    transaction_date: str | None = None
    notes: str | None = None
    # AI Evaluation M2 (P5): optional metadata-only link to the decision this
    # trade fulfills. See services/portfolio_transactions.py::execute_buy docstring.
    execution_decision_id: int | None = None


class TransactionSellBody(BaseModel):
    symbol: str
    shares: float
    price_per_share: float
    currency: str = "THB"
    exchange_rate: float = 1.0
    transaction_date: str | None = None
    notes: str | None = None
    remove_if_zero: bool = True
    execution_decision_id: int | None = None


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
        "execution_decision_id": tx.execution_decision_id,
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

    symbol = _normalize_transaction_symbol(body.symbol)

    if body.shares <= 0:
        raise HTTPException(status_code=422, detail="shares must be positive")
    if body.price_per_share <= 0:
        raise HTTPException(status_code=422, detail="price_per_share must be positive")

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
        currency=body.currency,
        exchange_rate=body.exchange_rate,
        transaction_date=tx_date,
        notes=body.notes,
        sector=sector,
        execution_decision_id=body.execution_decision_id,
    )
    _analytics_invalidate(portfolio_id)
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

    symbol = _normalize_transaction_symbol(body.symbol)

    if body.shares <= 0:
        raise HTTPException(status_code=422, detail="shares must be positive")
    if body.price_per_share <= 0:
        raise HTTPException(status_code=422, detail="price_per_share must be positive")

    tx_date = _parse_tx_date(body.transaction_date)

    try:
        result = execute_sell(
            db=db,
            ws_id=ws,
            portfolio_id=portfolio_id,
            symbol=symbol,
            shares=body.shares,
            price_per_share=body.price_per_share,
            currency=body.currency,
            exchange_rate=body.exchange_rate,
            transaction_date=tx_date,
            notes=body.notes,
            remove_if_zero=body.remove_if_zero,
            execution_decision_id=body.execution_decision_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    _analytics_invalidate(portfolio_id)
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
        q = q.filter(Transaction.symbol == _normalize_transaction_symbol(symbol))

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

    symbol = _normalize_transaction_symbol(body.symbol)
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


class TransactionQuantityCorrectionBody(BaseModel):
    symbol: str
    shares_delta: float
    price_per_share: float
    transaction_date: str | None = None
    notes: str | None = None


@app.post("/portfolios/{portfolio_id}/transactions/quantity-correction", status_code=201)
async def transaction_quantity_correction(
    portfolio_id: int,
    body: TransactionQuantityCorrectionBody,
    db: Session = Depends(get_db),
) -> dict:
    """Apply a manual share-count correction to an existing position.

    shares_delta is signed: positive adds shares, negative removes shares.
    Records a QUANTITY_CORRECTION transaction so the snapshot engine strips
    the equity change from investment_return_pct.
    """
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if body.shares_delta == 0:
        raise HTTPException(status_code=422, detail="shares_delta must be non-zero")
    if body.price_per_share <= 0:
        raise HTTPException(status_code=422, detail="price_per_share must be positive")

    symbol = _normalize_transaction_symbol(body.symbol)
    tx_date = _parse_tx_date(body.transaction_date)
    try:
        return execute_quantity_correction(
            db=db,
            ws_id=ws,
            portfolio_id=portfolio_id,
            symbol=symbol,
            shares_delta=body.shares_delta,
            price_per_share=body.price_per_share,
            transaction_date=tx_date,
            notes=body.notes,
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

    symbol = _normalize_transaction_symbol(body.symbol) if body.symbol else None
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
        "investment_return_pct": getattr(s, "investment_return_pct", None),
        "investment_return_amount": getattr(s, "investment_return_amount", None),
        "net_external_cash_flow": getattr(s, "net_external_cash_flow", None),
        "imported_asset_value": getattr(s, "imported_asset_value", None),
        "manual_adjustment_value": getattr(s, "manual_adjustment_value", None),
        # Period return decomposition — transparent breakdown of what drove the return
        "period_realized_pnl": getattr(s, "period_realized_pnl", None),
        "period_dividend_income": getattr(s, "period_dividend_income", None),
        "period_fees_paid": getattr(s, "period_fees_paid", None),
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
        result = await generate_daily_snapshot(
            db=db,
            portfolio_id=body.portfolio_id,
            workspace_id=ws,
            snapshot_date=body.snapshot_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except SnapshotCoverageError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "snapshot_coverage_insufficient",
                "message": (
                    f"Snapshot aborted: market price coverage {exc.successful}/{exc.total} "
                    f"({exc.successful / exc.total * 100:.0f}%) is below the 90% threshold."
                ),
                "portfolio_id": exc.portfolio_id,
                "date": exc.date,
                "coverage": {"total": exc.total, "successful": exc.successful},
                "missing_symbols": exc.missing,
            },
        )
    _analytics_invalidate(body.portfolio_id)
    return result


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
            {"date": "2026-05-22", "portfolio": 103.2, "bm_SET": 101.5, "bm_QQQ": 101.5},
          ]
        }

    Missing observations (market holidays, null DB rows) are forward-filled
    (LOCF) so the timeline is continuous; a value is None only before the
    series' first observation.
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

    # Build a chained return index anchored at 100.0 on base_date.
    # Uses investment_return_pct (capital-injection-stripped) so that importing
    # positions, deposits, or quantity corrections never create artificial spikes.
    # Falls back to daily_return_pct for snapshots generated before the
    # accounting fix, and defaults to 0.0 when both are NULL (e.g. first row).
    portfolio_index: dict[str, float] = {}
    _running_idx = 100.0
    for _snap in snap_rows:
        if not portfolio_index:
            portfolio_index[_snap.snapshot_date] = 100.0
        else:
            _ret = _snap.investment_return_pct
            if _ret is None:
                _ret = _snap.daily_return_pct
            if _ret is None:
                _ret = 0.0
            _running_idx = _running_idx * (1.0 + _ret / 100.0)
            portfolio_index[_snap.snapshot_date] = round(_running_idx, 4)
        _running_idx = portfolio_index[_snap.snapshot_date]

    # Parse requested benchmark symbols
    bench_symbols: list[str] = [s.strip() for s in benchmarks.split(",") if s.strip()]

    # Load benchmark prices for those symbols.
    # Data-integrity filter: sync_prices.py historically wrote close_price=0.0
    # rows with sync_status="error" on fetch failures. A 0.0 anchor poisons the
    # entire series (bv > 0 check fails → every point renders as None), so
    # exclude invalid rows BEFORE anchor discovery and return calculations.
    # sync_status semantics: "ok"/"stale" = usable price; NULL = legacy rows
    # written before Phase S.3 (scheduler, manual seed) — treated as valid for
    # backward compatibility; "error" = fabricated row, never usable.
    bench_map: dict[str, dict[str, float]] = {sym: {} for sym in bench_symbols}
    bench_base: dict[str, float] = {}

    if bench_symbols:
        bm_rows = (
            db.query(BenchmarkPrice)
            .filter(
                BenchmarkPrice.symbol.in_(bench_symbols),
                BenchmarkPrice.close_price > 0,
                sa_or(
                    BenchmarkPrice.sync_status.in_(["ok", "stale"]),
                    BenchmarkPrice.sync_status.is_(None),
                ),
            )
            .order_by(BenchmarkPrice.price_date.asc())
            .all()
        )
        for row in bm_rows:
            bench_map[row.symbol][row.price_date] = row.close_price

        # Anchor each benchmark to the closest available VALID price on or
        # after base_date (bench_map now contains only close_price > 0 rows).
        for sym in bench_symbols:
            dated = {d: v for d, v in bench_map[sym].items() if d >= base_date}
            if dated:
                anchor_date = min(dated.keys())
                bench_base[sym] = dated[anchor_date]

    # Keep only benchmarks that have at least one valid anchored observation.
    # Symbols with no valid rows degrade to an empty series (dropped from the
    # legend + data keys) instead of rendering an all-None line or raising.
    valid_bench_symbols: list[str] = [sym for sym in bench_symbols if sym in bench_base]

    # Collect all dates from portfolio + all valid benchmarks, sorted
    all_dates: set[str] = set(portfolio_index.keys())
    for sym in valid_bench_symbols:
        all_dates.update(d for d in bench_map[sym] if d >= base_date)
    sorted_dates = sorted(all_dates)

    # Build flat recharts data array.
    # Forward-fill (LOCF): when one market is closed on a date present in the
    # union timeline (e.g. SET holiday Jun 1–3 while QQQ trades), carry the
    # last observed index value forward so every row is fully populated and
    # the chart renders a continuous line. Dates before a series' first
    # observation remain None (nothing to carry forward yet).
    data: list[dict] = []
    last_portfolio: float | None = None
    last_bench: dict[str, float | None] = {sym: None for sym in valid_bench_symbols}
    for d in sorted_dates:
        row: dict = {"date": d}

        # Portfolio — cumulative return index (base=100, capital-injection-stripped)
        pv = portfolio_index.get(d)
        if pv is not None:
            last_portfolio = pv
        row["portfolio"] = last_portfolio

        # Each benchmark — normalised to base=100 from its own anchor price
        for sym in valid_bench_symbols:
            key = bench_key(sym)
            bv = bench_base.get(sym)
            price = bench_map[sym].get(d)
            if price is not None and bv and bv > 0:
                last_bench[sym] = round(price / bv * 100, 4)
            row[key] = last_bench[sym]

        data.append(row)

    # Series metadata for the frontend legend / line colours.
    # Benchmarks with no valid price rows are omitted (empty benchmark series)
    # rather than emitted as an all-None line.
    series = [
        {"key": "portfolio", "label": portfolio.name, "type": "portfolio", "symbol": None}
    ] + [
        {
            "key": bench_key(sym),
            "label": benchmark_label(sym),
            "type": "benchmark",
            "symbol": sym,
        }
        for sym in valid_bench_symbols
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


@app.post("/admin/repair-shadow-portfolios")
async def admin_repair_shadow_portfolios(db: Session = Depends(get_db)) -> dict:
    """One-time repair for shadow portfolios stuck at 0.00% return.

    Converts price_frozen dollar-value holdings to real share counts using
    historical PortfolioSnapshot prices, rebuilds empty inception holdings
    from linked decision/recommendation allocations, and re-derives the full
    ShadowPortfolioSnapshot history so AI-vs-Human realized outcomes reflect
    real market moves instead of a flat 0.00%.
    """
    from services.decision_memory.shadow_tracker import repair_shadow_portfolios

    ws = _ws_id(db)
    results = repair_shadow_portfolios(db, ws)
    repaired = sum(1 for r in results if r.get("status") == "repaired")
    return {
        "results": results,
        "shadows_total": len(results),
        "shadows_repaired": repaired,
    }


@app.post("/admin/backfill-snapshot-allocations")
async def admin_backfill_snapshot_allocations(db: Session = Depends(get_db)) -> dict:
    """Backfill projected_allocations_json on existing RecommendationSnapshot rows.

    snapshot_writer.py previously read r.get("layer2").get("allocations") but the
    optimizer stores allocations at r["target_allocations"] — so every snapshot was
    written with projected_allocations_json=NULL, breaking ACTIVE_MODEL shadow creation.

    This endpoint reads optimizer_history.result_json for each snapshot that is missing
    allocations and writes the correct target_allocations list.  After running this,
    trigger a new optimizer run (or call /admin/reset-active-model-inception) so the
    ACTIVE_MODEL shadows rebalance with real holdings.
    """
    from models.database import RecommendationSnapshot, OptimizerHistory

    ws = _ws_id(db)
    snaps = (
        db.query(RecommendationSnapshot)
        .filter(
            RecommendationSnapshot.workspace_id == ws,
            RecommendationSnapshot.projected_allocations_json.is_(None),
            RecommendationSnapshot.optimizer_history_id.isnot(None),
        )
        .all()
    )

    updated = 0
    skipped_no_history = 0
    skipped_no_allocs = 0

    for snap in snaps:
        oh = db.query(OptimizerHistory).filter_by(id=snap.optimizer_history_id).first()
        if not oh or not oh.result_json:
            skipped_no_history += 1
            continue
        try:
            result = _json.loads(oh.result_json)
        except Exception:
            skipped_no_history += 1
            continue

        target_allocs = result.get("target_allocations")
        if not target_allocs:
            skipped_no_allocs += 1
            continue

        snap.projected_allocations_json = _json.dumps(target_allocs)
        # Also backfill layer1/2/3 while we have the result
        if not snap.layer1_output_json:
            snap.layer1_output_json = _json.dumps(result["layer1_result"]) if result.get("layer1_result") else None
        if not snap.layer2_output_json:
            snap.layer2_output_json = _json.dumps(result["layer2_result"]) if result.get("layer2_result") else None
        if not snap.layer3_output_json:
            snap.layer3_output_json = _json.dumps(result["layer3_result"]) if result.get("layer3_result") else None
        updated += 1

    db.commit()
    _log.info("backfill_snapshot_allocations: updated=%d skipped_no_history=%d skipped_no_allocs=%d",
              updated, skipped_no_history, skipped_no_allocs)
    return {
        "snapshots_examined": len(snaps),
        "updated": updated,
        "skipped_no_history": skipped_no_history,
        "skipped_no_allocs": skipped_no_allocs,
    }


@app.post("/admin/reset-active-model-inception")
async def admin_reset_active_model_inception(db: Session = Depends(get_db)) -> dict:
    """Reset ACTIVE_MODEL shadow inception to today's date and current NAV.

    Clears all ShadowPortfolioSnapshot rows and resets inception_date /
    inception_value for every active ACTIVE_MODEL shadow in the workspace.

    Call once after deploying the Option B shadow rebalancing fix to discard
    previously corrupted (always-0%) history and start a clean cumulative
    track record from the current point in time.
    """
    from services.decision_memory.shadow_tracker import reset_active_model_inception

    ws = _ws_id(db)
    results = await asyncio.to_thread(reset_active_model_inception, db, ws)
    return {
        "results": results,
        "count": len(results),
        "reset": sum(1 for r in results if r.get("status") == "reset"),
    }


@app.post("/admin/recalculate-cost-basis")
async def admin_recalculate_cost_basis(
    from_date: str = "2026-05-27",
    dry_run: bool = False,
    db: Session = Depends(get_db),
) -> dict:
    """Replay transaction history with the broker-grade fee formula.

    What changes for each portfolio:
      1. Transaction.fees  → commission + trading_fee + clearing_fee (pre-VAT)
      2. Transaction.taxes → VAT amount
      3. PortfolioItem.avg_cost → rebuilt using fee-inclusive weighted average
      4. SELL notes        → Realized P&L figure updated to match new avg_cost
      5. PortfolioSnapshot rows on or after from_date → regenerated

    The total fee per transaction is mathematically identical to the old formula
    (0.00157 × 1.07 = sum of all components × 1.07), so cash balances are
    unchanged.  Only the fees/taxes split, avg_cost, and realized P&L wording
    are different.

    Set dry_run=true to preview affected counts without writing to the DB.
    """
    import re as _re
    from decimal import Decimal as _Dec, ROUND_HALF_UP as _RHU
    from services.broker_fees import calc_fees as _calc_fees, resolve_fee_profile as _resolve_profile

    _PNLRE = re.compile(r"^Realized P&L:\s*([-+]?\d+\.?\d*)\.\s*")
    _QUANT6 = _Dec("0.000001")

    def _d(v: float) -> _Dec:
        return _Dec(str(v))

    def _f(v: _Dec) -> float:
        return float(v.quantize(_QUANT6, rounding=_RHU))

    ws = _ws_id(db)
    cutoff = datetime.strptime(from_date, "%Y-%m-%d")

    portfolios = db.query(Portfolio).filter_by(workspace_id=ws).all()

    total_tx_updated = 0
    total_holdings_updated = 0
    total_snapshots_regenerated = 0
    snapshot_errors: list[str] = []

    for portfolio in portfolios:
        # ── Step 1: Re-split fees/taxes for BUY/SELL from from_date ──────────
        recent_txs = db.query(Transaction).filter(
            Transaction.portfolio_id == portfolio.id,
            Transaction.transaction_type.in_(["BUY", "SELL"]),
            Transaction.created_at >= cutoff,
        ).all()

        for tx in recent_txs:
            if tx.shares and tx.price_per_share:
                gross = _d(tx.shares) * _d(tx.price_per_share)
                profile = _resolve_profile(tx.symbol or "")
                bd = _calc_fees(gross, profile)
                if not dry_run:
                    tx.fees  = _f(bd.total_fees_excl_vat)
                    tx.taxes = _f(bd.vat)
                total_tx_updated += 1

        # ── Step 2: Full cost-basis replay (all transactions) ─────────────────
        all_txs = (
            db.query(Transaction)
            .filter(
                Transaction.portfolio_id == portfolio.id,
                Transaction.transaction_type.in_(["BUY", "SELL", "INITIAL_POSITION"]),
            )
            .order_by(Transaction.transaction_date, Transaction.id)
            .all()
        )

        # virtual holdings: {symbol: {shares: Decimal, avg_cost: Decimal}}
        virt: dict[str, dict] = {}

        for tx in all_txs:
            sym = tx.symbol
            if not sym or not tx.shares or not tx.price_per_share:
                continue

            d_sh  = _d(tx.shares)
            d_px  = _d(tx.price_per_share)

            if tx.transaction_type == "BUY":
                gross = d_sh * d_px
                profile = _resolve_profile(sym)
                bd = _calc_fees(gross, profile)
                net_cost = bd.net_buy_amount()   # fee-inclusive total cash out

                if sym not in virt:
                    virt[sym] = {"shares": d_sh, "avg_cost": net_cost / d_sh}
                else:
                    h = virt[sym]
                    new_sh  = h["shares"] + d_sh
                    new_avg = (h["shares"] * h["avg_cost"] + net_cost) / new_sh
                    virt[sym] = {"shares": new_sh, "avg_cost": new_avg}

            elif tx.transaction_type == "INITIAL_POSITION":
                d_avg = d_px
                if sym not in virt:
                    virt[sym] = {"shares": d_sh, "avg_cost": d_avg}
                else:
                    h = virt[sym]
                    new_sh  = h["shares"] + d_sh
                    new_avg = (h["shares"] * h["avg_cost"] + d_sh * d_avg) / new_sh
                    virt[sym] = {"shares": new_sh, "avg_cost": new_avg}

            elif tx.transaction_type == "SELL":
                if sym not in virt:
                    continue
                h      = virt[sym]
                avg_at_sell = h["avg_cost"]

                gross   = d_sh * d_px
                profile = _resolve_profile(sym)
                bd      = _calc_fees(gross, profile)
                pnl     = (d_px - avg_at_sell) * d_sh - bd.total_fees_incl_vat

                # Update SELL notes for transactions from from_date
                if not dry_run and tx.created_at >= cutoff and tx.notes is not None:
                    m = _PNLRE.match(tx.notes)
                    user_note = tx.notes[m.end():] if m else tx.notes
                    pnl_str   = f"Realized P&L: {_f(pnl):+.4f}"
                    tx.notes  = f"{pnl_str}. {user_note}" if user_note else pnl_str

                new_sh = h["shares"] - d_sh
                if _f(new_sh) <= 0:
                    del virt[sym]
                else:
                    virt[sym] = {"shares": new_sh, "avg_cost": avg_at_sell}

        # ── Step 3: Update PortfolioItem.avg_cost ─────────────────────────────
        for sym, state in virt.items():
            item = db.query(PortfolioItem).filter_by(
                portfolio_id=portfolio.id, symbol=sym
            ).first()
            if item:
                new_avg = _f(state["avg_cost"])
                if abs(new_avg - item.avg_cost) > 0.0001:
                    if not dry_run:
                        item.avg_cost = new_avg
                    total_holdings_updated += 1

        if not dry_run:
            db.commit()

        # ── Step 4: Regenerate snapshots from from_date ───────────────────────
        if not dry_run:
            snaps = (
                db.query(PortfolioSnapshot)
                .filter(
                    PortfolioSnapshot.portfolio_id == portfolio.id,
                    PortfolioSnapshot.snapshot_date >= from_date,
                )
                .order_by(PortfolioSnapshot.snapshot_date)
                .all()
            )
            for snap in snaps:
                try:
                    await generate_daily_snapshot(db, portfolio.id, ws, snap.snapshot_date)
                    total_snapshots_regenerated += 1
                except Exception as exc:
                    msg = f"portfolio={portfolio.id} date={snap.snapshot_date}: {exc}"
                    snapshot_errors.append(msg)
                    _log.warning("[COST-BASIS REGEN] snapshot failed — %s", msg)

    return {
        "from_date": from_date,
        "dry_run": dry_run,
        "portfolios_processed": len(portfolios),
        "transactions_updated": total_tx_updated,
        "holdings_updated": total_holdings_updated,
        "snapshots_regenerated": total_snapshots_regenerated,
        "snapshot_errors": snapshot_errors,
    }


@app.get("/admin/validate-portfolio/{portfolio_id}")
async def admin_validate_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Accounting integrity audit for a single portfolio.

    Checks performed:
      1. NAV reconciliation — cash + live equity ≈ last snapshot total_value
      2. Cash ledger        — portfolio.cash_balance reconciles with transaction history
      3. Realized P/L       — sum of parsed SELL notes matches snapshot realized_pnl
      4. Negative shares    — any PortfolioItem with shares ≤ 0

    Returns a structured report with pass/fail per check and the computed deltas.
    Designed as a diagnostic tool; it does not mutate any data.
    """
    ws = _ws_id(db)
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.workspace_id == ws,
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    items = db.query(PortfolioItem).filter_by(portfolio_id=portfolio_id).all()

    # ── Fetch live prices ─────────────────────────────────────────────────────
    prices_list = await asyncio.gather(*[
        asyncio.to_thread(fetch_price_info, item.symbol)
        for item in items
    ]) if items else []
    price_map: dict = {
        item.symbol: p.get("current_price")
        for item, p in zip(items, prices_list)
        if p.get("current_price")
    }

    live_equity = sum(
        item.shares * price_map[item.symbol]
        for item in items
        if item.symbol in price_map
    )
    live_cash   = portfolio.cash_balance or 0.0
    live_nav    = live_equity + live_cash

    # ── 1. NAV reconciliation vs latest snapshot ──────────────────────────────
    latest_snap = (
        db.query(PortfolioSnapshot)
        .filter_by(portfolio_id=portfolio_id)
        .order_by(PortfolioSnapshot.snapshot_date.desc())
        .first()
    )
    nav_check = {"status": "no_snapshot"}
    if latest_snap:
        delta = abs(live_nav - latest_snap.total_value)
        # Allow up to 2% drift (market movement since last snapshot is expected)
        nav_ok = delta / max(latest_snap.total_value, 1.0) < 0.02
        nav_check = {
            "status": "ok" if nav_ok else "drift",
            "live_nav": round(live_nav, 4),
            "snapshot_nav": round(latest_snap.total_value, 4),
            "snapshot_date": latest_snap.snapshot_date,
            "delta": round(delta, 4),
            "delta_pct": round(delta / max(latest_snap.total_value, 1.0) * 100, 2),
        }

    # ── 2. Cash ledger reconciliation ─────────────────────────────────────────
    all_txs = db.query(Transaction).filter_by(portfolio_id=portfolio_id).all()
    ledger_cash = 0.0
    for tx in all_txs:
        t = tx.transaction_type
        if t in ("DEPOSIT", "INITIAL_CASH"):
            ledger_cash += tx.total_amount
        elif t == "WITHDRAW":
            ledger_cash -= tx.total_amount
        elif t == "BUY":
            ledger_cash -= tx.total_amount   # total_amount = gross + fees
        elif t == "SELL":
            ledger_cash += tx.total_amount   # total_amount = net proceeds
        elif t == "DIVIDEND":
            ledger_cash += tx.total_amount

    cash_delta = abs(ledger_cash - live_cash)
    cash_check = {
        "status": "ok" if cash_delta < 0.10 else "mismatch",
        "ledger_computed": round(ledger_cash, 4),
        "portfolio_balance": round(live_cash, 4),
        "delta": round(cash_delta, 4),
    }

    # ── 3. Realized P/L from SELL notes ──────────────────────────────────────
    sell_txs = [t for t in all_txs if t.transaction_type == "SELL"]
    pnl_from_notes = 0.0
    pnl_unparsed   = 0
    _PNLRE = re.compile(r"Realized P&L:\s*([-+]?\d+\.?\d*)")
    for tx in sell_txs:
        if tx.notes:
            m = _PNLRE.search(tx.notes)
            if m:
                pnl_from_notes += float(m.group(1))
            else:
                pnl_unparsed += 1

    snap_realized = latest_snap.realized_pnl if latest_snap else None
    pnl_delta = abs(pnl_from_notes - (snap_realized or 0.0))
    pnl_check = {
        "status": "ok" if pnl_delta < 0.10 else "mismatch",
        "computed_from_notes": round(pnl_from_notes, 4),
        "snapshot_realized_pnl": round(snap_realized, 4) if snap_realized is not None else None,
        "delta": round(pnl_delta, 4),
        "unparsed_sell_notes": pnl_unparsed,
    }

    # ── 4. Negative-share positions ──────────────────────────────────────────
    neg_items = [item.symbol for item in items if item.shares <= 0]
    neg_check = {
        "status": "ok" if not neg_items else "error",
        "symbols_with_non_positive_shares": neg_items,
    }

    overall = "ok" if all(
        c.get("status") in ("ok", "no_snapshot", "drift")
        for c in [nav_check, cash_check, pnl_check, neg_check]
    ) else "issues_found"

    return {
        "portfolio_id": portfolio_id,
        "portfolio_name": portfolio.name,
        "overall": overall,
        "checks": {
            "nav_reconciliation": nav_check,
            "cash_ledger": cash_check,
            "realized_pnl": pnl_check,
            "negative_shares": neg_check,
        },
        "live_nav": round(live_nav, 4),
        "live_cash": round(live_cash, 4),
        "live_equity": round(live_equity, 4),
        "holdings_count": len(items),
    }


@app.get("/admin/cache-stats")
async def admin_cache_stats(db: Session = Depends(get_db)) -> dict:
    """Market data cache performance metrics.

    Returns:
      - In-process counters (hits, misses, stale_served, yahoo_requests, errors, …)
      - Derived rates (hit_rate_pct, avg_yahoo_latency_ms, requests_per_day_est)
      - DB snapshot: total cached entries, breakdown by cache_type, oldest/newest entry
    Note: counters reset when the server process restarts.
    """
    # ── In-process stats ──────────────────────────────────────────────────────
    stats = get_cache_stats()

    # ── DB snapshot ───────────────────────────────────────────────────────────
    total_entries = db.query(MarketDataCache).count()
    now = datetime.utcnow()
    live_entries  = db.query(MarketDataCache).filter(MarketDataCache.expires_at >= now).count()
    stale_entries = total_entries - live_entries

    # Breakdown by cache_type (quote / fundamental / history:…)
    type_rows = (
        db.query(MarketDataCache.cache_type, func.count(MarketDataCache.id))
        .group_by(MarketDataCache.cache_type)
        .all()
    )
    by_type = {row[0]: row[1] for row in type_rows}

    # Top-10 hottest symbols by hit_count
    hot_rows = (
        db.query(MarketDataCache.symbol, func.sum(MarketDataCache.hit_count).label("hits"))
        .group_by(MarketDataCache.symbol)
        .order_by(func.sum(MarketDataCache.hit_count).desc())
        .limit(10)
        .all()
    )
    hot_symbols = [{"symbol": r[0], "hits": r[1]} for r in hot_rows]

    oldest = db.query(func.min(MarketDataCache.fetched_at)).scalar()
    newest = db.query(func.max(MarketDataCache.fetched_at)).scalar()

    return {
        **stats,
        "db": {
            "total_entries":  total_entries,
            "live_entries":   live_entries,
            "stale_entries":  stale_entries,
            "by_cache_type":  by_type,
            "hot_symbols":    hot_symbols,
            "oldest_entry":   oldest.isoformat() + "Z" if oldest else None,
            "newest_entry":   newest.isoformat() + "Z" if newest else None,
        },
    }


@app.delete("/admin/cache-purge")
async def admin_cache_purge(
    symbol: str | None = None,
    cache_type: str | None = None,
    expired_only: bool = True,
    db: Session = Depends(get_db),
) -> dict:
    """Purge market_data_cache entries.

    Query params:
      symbol        — limit to one symbol (optional)
      cache_type    — limit to one cache_type, e.g. "quote" or "fundamental" (optional)
      expired_only  — if true (default), only delete entries past their expires_at
    """
    q = db.query(MarketDataCache)
    if symbol:
        q = q.filter(MarketDataCache.symbol == symbol)
    if cache_type:
        q = q.filter(MarketDataCache.cache_type == cache_type)
    if expired_only:
        q = q.filter(MarketDataCache.expires_at < datetime.utcnow())
    deleted = q.delete(synchronize_session=False)
    db.commit()
    return {"deleted": deleted, "symbol": symbol, "cache_type": cache_type, "expired_only": expired_only}


# ─── Phase 3A — Core Historical Analytics ────────────────────────────────────

@app.get("/analytics/performance-stats")
async def get_performance_stats(
    portfolio_id: int,
    benchmark: str = "^SET.BK,QQQ",
    include_equity_curve: bool = True,
    include_rolling_returns: bool = False,
    include_sector_evolution: bool = True,
    db: Session = Depends(get_db),
) -> dict:
    """Comprehensive portfolio analytics: return metrics, benchmark comparison,
    signal analytics, and allocation analytics.

    Query params:
        portfolio_id            — required; target portfolio
        benchmark               — comma-separated benchmark symbols (default: "^SET.BK,QQQ")
        include_equity_curve    — daily equity curve with drawdown (default: true)
        include_rolling_returns — 30-day rolling returns series (default: false)
        include_sector_evolution — sector allocation over time (default: true)

    Response shape:
        {
          portfolio_id, portfolio_name, generated_at,
          portfolio_metrics:  { cumulative_return_pct, annualized_return_pct,
                                volatility_pct, sharpe_ratio, max_drawdown,
                                monthly_win_rate, snapshot_count, date_range },
          benchmark_metrics:  { benchmarks: [{symbol, alpha, beta, r_squared,
                                              correlation, tracking_error_pct,
                                              information_ratio, aligned_days}] },
          signal_metrics:     { buy_win_rate, sell_accuracy,
                                average_holding_return, signal_decay,
                                total_signals, signals_by_action },
          allocation_metrics: { sector_contribution, top_contributors,
                                cash_utilization, concentration_risk },
          equity_curve?:      [{date, total_value, cumulative_return_pct,
                                drawdown_pct, daily_return_pct}],
          rolling_returns?:   [{date, rolling_return_pct, window_days}],
          sector_evolution?:  [{date, sector: weight_pct, ...}],
        }
    """
    ws = _ws_id(db)

    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.workspace_id == ws,
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # ── Cache check ────────────────────────────────────────────────────────────
    # Keyed on every param that affects the computed result — a stale entry from
    # a different benchmark/include-flag combo must never be served back.
    cache_group = f"full:{benchmark}:{include_equity_curve}:{include_rolling_returns}:{include_sector_evolution}"
    cached = _analytics_get_cached(portfolio_id, cache_group)
    if cached:
        return cached

    # ── Load snapshots (oldest first) ─────────────────────────────────────────
    snapshots = (
        db.query(PortfolioSnapshot)
        .filter(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.workspace_id == ws,
        )
        .order_by(PortfolioSnapshot.snapshot_date.asc())
        .all()
    )

    # ── Load benchmark prices aligned to snapshot date range ──────────────────
    benchmark_prices: dict[str, dict[str, float]] = {}
    if snapshots:
        bench_symbols = [s.strip() for s in benchmark.split(",") if s.strip()]
        from_date = snapshots[0].snapshot_date
        for sym in bench_symbols:
            rows = (
                db.query(BenchmarkPrice)
                .filter(
                    BenchmarkPrice.symbol == sym,
                    BenchmarkPrice.price_date >= from_date,
                )
                .order_by(BenchmarkPrice.price_date.asc())
                .all()
            )
            if rows:
                benchmark_prices[sym] = {r.price_date: r.close_price for r in rows}

    # ── Load signal history for this workspace ────────────────────────────────
    signals = (
        db.query(SignalHistory)
        .filter(SignalHistory.workspace_id == ws)
        .order_by(SignalHistory.recorded_at.asc())
        .all()
    )

    # ── Compute all metrics ───────────────────────────────────────────────────
    result: dict = {
        "portfolio_id": portfolio_id,
        "portfolio_name": portfolio.name,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "portfolio_metrics": build_portfolio_metrics(snapshots),
        "benchmark_metrics": build_benchmark_metrics(snapshots, benchmark_prices),
        "signal_metrics": build_signal_metrics(signals, snapshots),
        "allocation_metrics": build_allocation_metrics(snapshots),
    }

    # ── Optional chart-data blobs ─────────────────────────────────────────────
    if include_equity_curve:
        result["equity_curve"] = build_equity_curve(snapshots)
    if include_rolling_returns:
        result["rolling_returns"] = build_rolling_returns(snapshots, window=30)
    if include_sector_evolution:
        result["sector_evolution"] = build_sector_evolution(snapshots)

    _analytics_set_cached(portfolio_id, cache_group, result)
    return result


# ─── Factor Exposure Analysis ─────────────────────────────────────────────────

@app.get("/analytics/factor-exposure")
async def get_factor_exposure(
    portfolio_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Institutional-grade factor exposure analysis for a portfolio.

    Computes 5 weighted factor exposures using percentile-rank normalization
    within the current portfolio universe.  Cross-market bias between Thai SET
    and US stocks is eliminated because all ranking is relative.

    Query params:
        portfolio_id — required; must belong to the authenticated workspace

    Response shape:
        {
          portfolio_id, portfolio_name, generated_at,
          factor_exposures: {
            growth:   {score, label, description},
            value:    {score, label, description},
            dividend: {score, label, description},
            momentum: {score, label, description},
            quality:  {score, label, description},
          },
          style_classification: {
            primary, secondary, confidence, dominant_factors, rationale
          },
          per_stock_scores: [
            {symbol, sector, weight, scores: {growth,value,dividend,momentum,quality},
             data_coverage}
          ],
          raw_metrics_summary: {avg_pe, avg_roe, avg_revenue_growth, ...},
          sector_concentration: {
            sector_weights, top_sector, top_sector_weight,
            diversification_score, hhi, hhi_label, concentration_flags
          },
          metadata: {universe_size, data_quality_flags, normalization_method, computed_at},
        }

    Result is cached for 15 minutes; invalidated automatically when holdings change.
    """
    from services.analytics.factor_engine import compute_portfolio_factor_exposure

    ws = _ws_id(db)

    # Verify portfolio ownership before computing
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.workspace_id == ws,
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    result = await asyncio.to_thread(
        compute_portfolio_factor_exposure, db, portfolio_id, ws
    )

    if result.get("error") == "portfolio_not_found":
        raise HTTPException(status_code=404, detail="Portfolio not found")

    return result


# ─── Market Regime Detection ──────────────────────────────────────────────────

@app.get("/analytics/market-regime")
async def get_market_regime(
    db: Session = Depends(get_db),
) -> dict:
    """Detect the current market regime using multi-signal benchmark analysis.

    Classifies the macro environment into one of 7 states:
    RISK_ON | RISK_OFF | SIDEWAYS | HIGH_VOLATILITY |
    DEFENSIVE_REGIME | TRANSITION_RISK_ON | TRANSITION_RISK_OFF

    Signals: EMA20/50 trend alignment, rolling vol z-score, 30D drawdown,
    momentum persistence, cross-benchmark return dispersion, optional VIX.

    Response includes:
      - active regime + confidence
      - trend/volatility/drawdown/momentum scores (0-100)
      - regime duration (trading days)
      - previous regime + transition stability
      - transition warnings
      - per-benchmark signal breakdown
      - 30-day historical regime timeline
      - hard allocation constraints for the current regime
      - narrative text for display

    Result is cached for 30 minutes.
    """
    from services.analytics.regime_detector import detect_regime

    result = await asyncio.to_thread(detect_regime, db)
    return result


# ─── Operations Center (Phase 4C.1) ──────────────────────────────────────────

@app.get("/operations-center/status")
async def operations_center_status(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    """Unified Operations Center status — aggregates existing services only.

    Combines: latest portfolio snapshot (NAV / daily return / goal progress),
    market regime (60s TTL cache), latest optimizer consensus + active policy,
    6-station agent health (GREEN/YELLOW/RED from real backend state), and a
    deterministic plain-Thai MUJI translation block.  Presentation layer only —
    no optimizer/regime/policy logic is recomputed here.
    """
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == ws).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    from services.operations_center import build_operations_status

    return await asyncio.to_thread(build_operations_status, db, ws, portfolio_id)


@app.get("/operations-center/optimizer-progress")
async def operations_center_optimizer_progress(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    """Live optimizer run progress for the Operations Timeline (poll ~1.5s).

    Reads the in-memory run-progress registry written by /analyze/optimizer.
    Stages reflect the REAL pipeline position (data prep, context, L1/L2/L3,
    stabilization, save) — no simulated progress.
    """
    _ws_id(db)  # auth/workspace consistency (registry itself is per-process)
    from services.run_progress import get_progress

    return get_progress(portfolio_id)


# ─── Phase 3B.7 — Decision Memory System ─────────────────────────────────────

class ExecutionDecisionRequest(BaseModel):
    portfolio_id: int
    recommendation_snapshot_id: int
    decision: str                          # APPROVED | REJECTED | MANUAL_OVERRIDE
    approved_allocations: list[dict] | None = None
    rejected_symbols: list[str] | None = None
    override_notes: str | None = None
    create_static_shadow: bool = False     # auto-create a STATIC_FROZEN shadow
    # UX.2D structured override fields (all optional)
    override_type: str | None = None       # REJECT_SWAP | REPLACE_SYMBOL | …
    original_symbol: str | None = None    # symbol the AI recommended
    replacement_symbol: str | None = None # symbol human chose instead
    reason_category: str | None = None    # short category tag


@app.post("/optimizer/decisions")
async def record_execution_decision(
    body: ExecutionDecisionRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Record the action a user took after reviewing an optimizer recommendation.

    decision: APPROVED | REJECTED | MANUAL_OVERRIDE
    Optionally creates a STATIC_FROZEN shadow portfolio to track what would
    have happened had the recommendation been followed exactly.
    """
    ws = _ws_id(db)
    _VALID_DECISIONS = {"APPROVED", "REJECTED", "PARTIAL_EXECUTION", "MANUAL_OVERRIDE"}
    if body.decision.upper() not in _VALID_DECISIONS:
        raise HTTPException(status_code=400, detail=f"decision must be one of: {_VALID_DECISIONS}")

    snap = db.query(RecommendationSnapshot).filter_by(
        id=body.recommendation_snapshot_id,
        workspace_id=ws,
    ).first()
    if not snap:
        raise HTTPException(status_code=404, detail="recommendation_snapshot not found")

    oh = db.query(OptimizerHistory).filter_by(
        id=snap.optimizer_history_id,
        workspace_id=ws,
    ).first()

    from services.override_classifier import build_override_record
    override_rec = build_override_record(
        body.override_type, body.original_symbol,
        body.replacement_symbol, body.reason_category, body.override_notes,
    )

    now = datetime.utcnow()
    decision = UserExecutionDecision(
        workspace_id=ws,
        recommendation_snapshot_id=body.recommendation_snapshot_id,
        optimizer_history_id=snap.optimizer_history_id,
        portfolio_id=body.portfolio_id,
        decision=body.decision.upper(),
        approved_allocations_json=_json.dumps(body.approved_allocations) if body.approved_allocations else None,
        rejected_symbols_json=_json.dumps(body.rejected_symbols) if body.rejected_symbols else None,
        override_notes=override_rec["override_notes"],
        override_type=override_rec["override_type"],
        original_symbol=override_rec["original_symbol"],
        replacement_symbol=override_rec["replacement_symbol"],
        reason_category=override_rec["reason_category"],
        executed_at=now,
        created_at=now,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)

    result: dict = {
        "decision_id": decision.id,
        "decision": decision.decision,
        "recommendation_snapshot_id": body.recommendation_snapshot_id,
        "portfolio_id": body.portfolio_id,
        "executed_at": now.isoformat() + "Z",
    }

    # On APPROVED: always create both STATIC_FROZEN and ACTIVE_MODEL shadows
    if decision.decision == "APPROVED":
        from services.decision_memory.shadow_tracker import (
            create_static_frozen_shadow, create_active_model_shadow, value_shadow_portfolio,
        )
        try:
            static_result = create_static_frozen_shadow(db, decision.id, ws)
            static_shadow_id = static_result.get("shadow_id")
            if static_shadow_id:
                static_result["initial_snapshot"] = value_shadow_portfolio(db, int(static_shadow_id))
            result["static_shadow"] = static_result
        except Exception as exc:
            _log.warning("record_execution_decision: STATIC_FROZEN creation failed: %s", exc)
            result["static_shadow"] = {"error": str(exc)}
        try:
            active_result = create_active_model_shadow(
                db, body.portfolio_id, body.recommendation_snapshot_id, ws
            )
            active_shadow_id = active_result.get("shadow_id")
            if active_shadow_id:
                active_result["initial_snapshot"] = value_shadow_portfolio(db, int(active_shadow_id))
            result["active_model_shadow"] = active_result
        except Exception as exc:
            _log.warning("record_execution_decision: ACTIVE_MODEL creation failed: %s", exc)
            result["active_model_shadow"] = {"error": str(exc)}
    elif body.create_static_shadow:
        # Explicit flag on non-APPROVED decisions (REJECTED / MANUAL_OVERRIDE)
        try:
            from services.decision_memory.shadow_tracker import create_static_frozen_shadow, value_shadow_portfolio
            static_result = create_static_frozen_shadow(db, decision.id, ws)
            static_shadow_id = static_result.get("shadow_id")
            if static_shadow_id:
                static_result["initial_snapshot"] = value_shadow_portfolio(db, int(static_shadow_id))
            result["static_shadow"] = static_result
        except Exception as exc:
            _log.warning("record_execution_decision: shadow creation failed: %s", exc)
            result["static_shadow"] = {"error": str(exc)}

    # On APPROVED: trigger attribution computation in background (after shadows are created)
    if decision.decision == "APPROVED":
        def _run_attribution_bg(portfolio_id: int) -> None:
            try:
                from services.analytics.attribution_engine import compute_portfolio_attribution
                _bg_db = SessionLocal()
                try:
                    compute_portfolio_attribution(_bg_db, portfolio_id)
                finally:
                    _bg_db.close()
            except Exception as _attr_exc:
                _log.debug("record_execution_decision: attribution bg failed: %s", _attr_exc)

        import threading as _threading
        _threading.Thread(
            target=_run_attribution_bg,
            args=(body.portfolio_id,),
            daemon=True,
        ).start()

    return result


@app.get("/optimizer/decisions")
async def list_execution_decisions(
    portfolio_id: int | None = None,
    decision: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[dict]:
    """List user execution decisions, optionally filtered by portfolio or decision type."""
    ws = _ws_id(db)
    q = db.query(UserExecutionDecision).filter(UserExecutionDecision.workspace_id == ws)
    if portfolio_id:
        q = q.filter(UserExecutionDecision.portfolio_id == portfolio_id)
    if decision:
        q = q.filter(UserExecutionDecision.decision == decision.upper())
    rows = q.order_by(UserExecutionDecision.executed_at.desc()).limit(min(limit, 200)).all()
    return [
        {
            "id": r.id,
            "portfolio_id": r.portfolio_id,
            "recommendation_snapshot_id": r.recommendation_snapshot_id,
            "optimizer_history_id": r.optimizer_history_id,
            "decision": r.decision,
            "override_notes": r.override_notes,
            "override_type": r.override_type,
            "original_symbol": r.original_symbol,
            "replacement_symbol": r.replacement_symbol,
            "reason_category": r.reason_category,
            "executed_at": r.executed_at.isoformat() + "Z" if r.executed_at else None,
            "created_at": r.created_at.isoformat() + "Z" if r.created_at else None,
        }
        for r in rows
    ]


@app.get("/optimizer/decisions/{decision_id}")
async def get_execution_decision(decision_id: int, db: Session = Depends(get_db)) -> dict:
    """Return a single execution decision with its linked recommendation snapshot metadata."""
    ws = _ws_id(db)
    row = db.query(UserExecutionDecision).filter_by(id=decision_id, workspace_id=ws).first()
    if not row:
        raise HTTPException(status_code=404, detail="Decision not found")

    snap = db.query(RecommendationSnapshot).filter_by(
        id=row.recommendation_snapshot_id
    ).first()

    return {
        "id": row.id,
        "portfolio_id": row.portfolio_id,
        "decision": row.decision,
        "override_notes": row.override_notes,
        "override_type": row.override_type,
        "original_symbol": row.original_symbol,
        "replacement_symbol": row.replacement_symbol,
        "reason_category": row.reason_category,
        "approved_allocations": _json.loads(row.approved_allocations_json) if row.approved_allocations_json else None,
        "rejected_symbols": _json.loads(row.rejected_symbols_json) if row.rejected_symbols_json else None,
        "executed_at": row.executed_at.isoformat() + "Z" if row.executed_at else None,
        "recommendation_snapshot": {
            "id": snap.id,
            "persona": snap.persona,
            "total_portfolio_value": snap.total_portfolio_value,
            "created_at": snap.created_at.isoformat() + "Z" if snap.created_at else None,
            "regime": _json.loads(snap.regime_snapshot_json) if snap.regime_snapshot_json else None,
            "consensus": _json.loads(snap.consensus_json) if snap.consensus_json else None,
            "projected_allocations": _json.loads(snap.projected_allocations_json) if snap.projected_allocations_json else None,
        } if snap else None,
    }


@app.get("/optimizer/snapshots/{snapshot_id}")
async def get_recommendation_snapshot(snapshot_id: int, db: Session = Depends(get_db)) -> dict:
    """Return the full RecommendationSnapshot for a given optimizer run."""
    ws = _ws_id(db)
    snap = db.query(RecommendationSnapshot).filter_by(id=snapshot_id, workspace_id=ws).first()
    if not snap:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    return {
        "id": snap.id,
        "optimizer_history_id": snap.optimizer_history_id,
        "portfolio_id": snap.portfolio_id,
        "persona": snap.persona,
        "total_portfolio_value": snap.total_portfolio_value,
        "regime": _json.loads(snap.regime_snapshot_json) if snap.regime_snapshot_json else None,
        "constraint_envelope": _json.loads(snap.constraint_envelope_json) if snap.constraint_envelope_json else None,
        "active_policy": _json.loads(snap.active_policy_json) if snap.active_policy_json else None,
        "layer1": _json.loads(snap.layer1_output_json) if snap.layer1_output_json else None,
        "layer2": _json.loads(snap.layer2_output_json) if snap.layer2_output_json else None,
        "layer3": _json.loads(snap.layer3_output_json) if snap.layer3_output_json else None,
        "consensus": _json.loads(snap.consensus_json) if snap.consensus_json else None,
        "portfolio_dna": _json.loads(snap.portfolio_dna_json) if snap.portfolio_dna_json else None,
        "style_drift": _json.loads(snap.style_drift_json) if snap.style_drift_json else None,
        "projected_allocations": _json.loads(snap.projected_allocations_json) if snap.projected_allocations_json else None,
        "created_at": snap.created_at.isoformat() + "Z" if snap.created_at else None,
    }


# ─── Shadow Portfolio endpoints ───────────────────────────────────────────────

class ShadowPortfolioRequest(BaseModel):
    portfolio_id: int
    shadow_type: str                       # STATIC_FROZEN | ACTIVE_MODEL
    execution_decision_id: int | None = None
    recommendation_snapshot_id: int | None = None


@app.post("/analytics/shadow-portfolios")
async def create_shadow_portfolio(
    body: ShadowPortfolioRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Create a shadow portfolio for paper-trading tracking.

    STATIC_FROZEN: requires execution_decision_id — freezes state at decision time.
    ACTIVE_MODEL:  requires recommendation_snapshot_id — hypothetical 100% compliant portfolio.
    """
    ws = _ws_id(db)
    shadow_type = body.shadow_type.upper()
    if shadow_type not in {"STATIC_FROZEN", "ACTIVE_MODEL"}:
        raise HTTPException(status_code=400, detail="shadow_type must be STATIC_FROZEN or ACTIVE_MODEL")

    if shadow_type == "STATIC_FROZEN":
        if not body.execution_decision_id:
            raise HTTPException(status_code=400, detail="execution_decision_id required for STATIC_FROZEN")
        from services.decision_memory.shadow_tracker import create_static_frozen_shadow
        result = await asyncio.to_thread(create_static_frozen_shadow, db, body.execution_decision_id, ws)
    else:
        if not body.recommendation_snapshot_id:
            raise HTTPException(status_code=400, detail="recommendation_snapshot_id required for ACTIVE_MODEL")
        from services.decision_memory.shadow_tracker import create_active_model_shadow
        result = await asyncio.to_thread(
            create_active_model_shadow, db, body.portfolio_id, body.recommendation_snapshot_id, ws
        )

    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/analytics/shadow-portfolios")
async def list_shadow_portfolios(
    portfolio_id: int | None = None,
    shadow_type: str | None = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
) -> list[dict]:
    """List shadow portfolios for the workspace."""
    ws = _ws_id(db)
    q = db.query(ShadowPortfolio).filter(ShadowPortfolio.workspace_id == ws)
    if portfolio_id:
        q = q.filter(ShadowPortfolio.portfolio_id == portfolio_id)
    if shadow_type:
        q = q.filter(ShadowPortfolio.shadow_type == shadow_type.upper())
    if active_only:
        q = q.filter(ShadowPortfolio.is_active == True)  # noqa: E712
    rows = q.order_by(ShadowPortfolio.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "portfolio_id": r.portfolio_id,
            "shadow_type": r.shadow_type,
            "name": r.name,
            "inception_date": r.inception_date,
            "inception_value": r.inception_value,
            "current_value": r.current_value,
            "inception_return_pct": r.inception_return_pct,
            "is_active": r.is_active,
            "last_valued_at": r.last_valued_at.isoformat() + "Z" if r.last_valued_at else None,
            "recommendation_snapshot_id": r.recommendation_snapshot_id,
            "execution_decision_id": r.execution_decision_id,
            "created_at": r.created_at.isoformat() + "Z" if r.created_at else None,
        }
        for r in rows
    ]


@app.get("/analytics/shadow-portfolios/{shadow_id}/performance")
async def get_shadow_portfolio_performance(
    shadow_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Return performance data for a shadow portfolio including daily snapshot history."""
    ws = _ws_id(db)
    shadow = db.query(ShadowPortfolio).filter_by(id=shadow_id, workspace_id=ws).first()
    if not shadow:
        raise HTTPException(status_code=404, detail="Shadow portfolio not found")

    # Trigger a fresh valuation for today
    from services.decision_memory.shadow_tracker import value_shadow_portfolio
    today_valuation = await asyncio.to_thread(value_shadow_portfolio, db, shadow_id)

    snapshots = (
        db.query(ShadowPortfolioSnapshot)
        .filter_by(shadow_portfolio_id=shadow_id)
        .order_by(ShadowPortfolioSnapshot.snapshot_date)
        .all()
    )

    return {
        "shadow_id": shadow_id,
        "shadow_type": shadow.shadow_type,
        "name": shadow.name,
        "inception_date": shadow.inception_date,
        "inception_value": shadow.inception_value,
        "current_value": shadow.current_value,
        "inception_return_pct": shadow.inception_return_pct,
        "today_valuation": today_valuation,
        "history": [
            {
                "date": s.snapshot_date,
                "total_value": s.total_value,
                "return_pct_since_inception": s.return_pct_since_inception,
                "daily_return_pct": s.daily_return_pct,
                "benchmark_return_pct": s.benchmark_return_pct,
                "alpha": s.alpha,
            }
            for s in snapshots
        ],
    }


@app.post("/analytics/shadow-portfolios/{shadow_id}/value")
async def trigger_shadow_valuation(
    shadow_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Trigger an immediate paper-valuation for a shadow portfolio."""
    ws = _ws_id(db)
    shadow = db.query(ShadowPortfolio).filter_by(id=shadow_id, workspace_id=ws).first()
    if not shadow:
        raise HTTPException(status_code=404, detail="Shadow portfolio not found")

    from services.decision_memory.shadow_tracker import value_shadow_portfolio
    result = await asyncio.to_thread(value_shadow_portfolio, db, shadow_id)
    return result


# ─── Attribution & Calibration endpoints (structural stubs) ──────────────────

@app.get("/analytics/attribution/{shadow_id}")
async def get_attribution(
    shadow_id: int,
    start: str | None = None,
    end: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """Compute Brinson-Hood-Beebower alpha attribution for a shadow portfolio.

    Returns selection alpha, allocation alpha, and interaction effect.
    Sector-level decomposition is a structural stub pending per-sector benchmark data.

    Query params:
      start: "YYYY-MM-DD" (default: shadow inception_date)
      end:   "YYYY-MM-DD" (default: today)
    """
    ws = _ws_id(db)
    shadow = db.query(ShadowPortfolio).filter_by(id=shadow_id, workspace_id=ws).first()
    if not shadow:
        raise HTTPException(status_code=404, detail="Shadow portfolio not found")

    from services.decision_memory.attribution import compute_attribution, get_attribution_summary
    period_start = start or shadow.inception_date
    period_end = end or datetime.utcnow().strftime("%Y-%m-%d")

    result = await asyncio.to_thread(compute_attribution, db, shadow_id, period_start, period_end)
    history = get_attribution_summary(db, shadow_id)

    return {
        "shadow_id": shadow_id,
        "current": result,
        "history": history,
    }


@app.get("/analytics/calibration")
async def get_confidence_calibration(
    portfolio_id: int | None = None,
    lookback_days: int = 30,
    refresh: bool = False,
    db: Session = Depends(get_db),
) -> dict:
    """Return confidence calibration results for the workspace.

    Evaluates whether consensus_strength_score, policy_alignment_score, and
    regime confidence predicted real outcomes over the lookback window.

    Set refresh=true to recompute (otherwise returns the latest stored record).

    Structural stub: full calibration math requires accumulated SignalHistory
    with realized price data.  Current output includes regime stability and
    skeleton signal accuracy.
    """
    ws = _ws_id(db)
    from services.decision_memory.calibration import compute_calibration, get_latest_calibration

    if not refresh:
        latest = get_latest_calibration(db, ws)
        if latest:
            return {"source": "cached", "calibration": latest}

    result = await asyncio.to_thread(compute_calibration, db, ws, lookback_days)
    return {"source": "computed", "calibration": result}


# ─── Phase 3B.7B — Attribution Analytics & Human-vs-AI Benchmark Engine ──────

@app.get("/analytics/attribution-summary")
async def get_attribution_summary(
    portfolio_id: int,
    evaluation_window_days: int = 30,
    db: Session = Depends(get_db),
) -> dict:
    """Compute portfolio attribution vs shadow benchmarks.

    Returns actual portfolio returns vs STATIC_FROZEN and ACTIVE_MODEL shadow
    portfolios over the given window. Computes regret_score (AI model return −
    actual return), avoided_drawdown (how much more drawdown the frozen baseline
    experienced), and ai_outperformed flag.

    Requires at least one shadow portfolio to exist for this portfolio. Shadow
    portfolios are created automatically when execution decisions are recorded
    (STATIC_FROZEN) or when the ACTIVE_MODEL is initialized after an optimizer run.

    Query params:
      portfolio_id           : required
      evaluation_window_days : 7 | 14 | 30 | 60 | 90 (default 30)
    """
    ws = _ws_id(db)
    from services.analytics.attribution_engine import (
        compute_portfolio_attribution,
        get_attribution_summary as _get_summary,
    )

    current = await asyncio.to_thread(
        compute_portfolio_attribution, db, portfolio_id, evaluation_window_days
    )
    history = _get_summary(db, portfolio_id, limit=10)

    return {
        "portfolio_id": portfolio_id,
        "current": current,
        "history": history,
    }


@app.get("/analytics/human-vs-ai")
async def get_human_vs_ai_comparison(
    portfolio_id: int,
    evaluation_days: int = 90,
    db: Session = Depends(get_db),
) -> dict:
    """Compare human execution decisions against AI model recommendations.

    For each UserExecutionDecision in the evaluation window, measures:
      - actual portfolio return since decision date
      - shadow portfolio return since decision date
      - return_delta (shadow − actual): positive = AI was better
      - hit_rate: % of decisions where AI shadow outperformed actual execution
      - mean return/volatility/drawdown deltas across all decisions

    Null-safe for portfolios with no decisions or insufficient snapshot data.
    """
    _ws_id(db)
    from services.analytics.human_vs_ai import compare_human_vs_ai

    result = await asyncio.to_thread(compare_human_vs_ai, db, portfolio_id, evaluation_days)
    return result


@app.get("/analytics/regime-attribution")
async def get_regime_attribution(
    portfolio_id: int,
    lookback_days: int = 90,
    db: Session = Depends(get_db),
) -> dict:
    """Group portfolio daily returns by market regime.

    Joins PortfolioSnapshot daily_return_pct with RegimeSnapshot labels to
    show which market conditions the portfolio performed best/worst in.
    Also surfaces optimizer run statistics per regime (avg opportunity score,
    rebalance rate).

    Null-safe: returns status='no_snapshot_data' or 'no_regime_overlap'
    when data is insufficient.
    """
    _ws_id(db)
    from services.analytics.regime_attribution import compute_regime_attribution

    result = await asyncio.to_thread(compute_regime_attribution, db, portfolio_id, lookback_days)
    return result


@app.get("/analytics/data-readiness")
async def get_analytics_data_readiness(
    portfolio_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Diagnostic endpoint: full data-pipeline health report for a portfolio.

    Returns counts for every table in the attribution pipeline and a plain-
    English list of blockers explaining why metrics may be empty.  Use this
    when attribution, shadow, or calibration cards show no data.
    """
    from models.database import (
        PortfolioSnapshot, RecommendationSnapshot, UserExecutionDecision,
        ShadowPortfolio, ShadowPortfolioSnapshot, AttributionMetric,
        ConfidenceCalibrationRecord, RegimeSnapshot, BenchmarkPrice,
    )
    ws = _ws_id(db)

    portfolio_snaps = db.query(PortfolioSnapshot).filter_by(portfolio_id=portfolio_id).count()
    rec_snaps = db.query(RecommendationSnapshot).filter_by(portfolio_id=portfolio_id).count()
    decisions_total = db.query(UserExecutionDecision).filter_by(portfolio_id=portfolio_id).count()
    approved_decisions = db.query(UserExecutionDecision).filter_by(
        portfolio_id=portfolio_id, decision="APPROVED"
    ).count()

    shadow_rows = (
        db.query(ShadowPortfolio)
        .filter_by(portfolio_id=portfolio_id, workspace_id=ws, is_active=True)
        .all()
    )
    shadow_summary = []
    for s in shadow_rows:
        snap_count = (
            db.query(ShadowPortfolioSnapshot)
            .filter_by(shadow_portfolio_id=s.id)
            .count()
        )
        latest = (
            db.query(ShadowPortfolioSnapshot)
            .filter_by(shadow_portfolio_id=s.id)
            .order_by(ShadowPortfolioSnapshot.snapshot_date.desc())
            .first()
        )
        shadow_summary.append({
            "id": s.id,
            "type": s.shadow_type,
            "inception_date": s.inception_date,
            "snapshot_count": snap_count,
            "latest_snapshot": latest.snapshot_date if latest else None,
            "last_valued_at": s.last_valued_at.isoformat() + "Z" if s.last_valued_at else None,
        })

    attribution_records = db.query(AttributionMetric).filter_by(portfolio_id=portfolio_id).count()
    regime_snaps = db.query(RegimeSnapshot).count()
    benchmark_prices = db.query(BenchmarkPrice).count()
    calibration_records = db.query(ConfidenceCalibrationRecord).filter_by(workspace_id=ws).count()

    latest_ps = (
        db.query(PortfolioSnapshot)
        .filter_by(portfolio_id=portfolio_id)
        .order_by(PortfolioSnapshot.snapshot_date.desc())
        .first()
    )
    latest_rs = (
        db.query(RecommendationSnapshot)
        .filter_by(portfolio_id=portfolio_id)
        .order_by(RecommendationSnapshot.created_at.desc())
        .first()
    )

    blockers: list[str] = []
    if portfolio_snaps < 2:
        blockers.append(
            f"Need ≥2 portfolio snapshots for return calculations "
            f"(have {portfolio_snaps} — scheduled at 17:45 ICT)"
        )
    if rec_snaps == 0:
        blockers.append("No recommendation snapshots — run the optimizer at least once")
    if not shadow_rows:
        blockers.append(
            "No active shadow portfolios — the optimizer now auto-creates an ACTIVE_MODEL "
            "shadow on each run; or record an APPROVED decision to create a STATIC_FROZEN shadow"
        )
    elif all(s["snapshot_count"] == 0 for s in shadow_summary):
        blockers.append(
            "Shadow portfolios exist but have no snapshots yet — "
            "initial valuation fires in the background after the optimizer run; "
            "daily re-valuation at 17:45 ICT"
        )
    if regime_snaps == 0:
        blockers.append(
            "No regime snapshots — run the optimizer to generate market regime data"
        )
    if benchmark_prices == 0:
        blockers.append(
            "No benchmark prices — stored at 17:45 ICT alongside portfolio snapshots"
        )

    return {
        "portfolio_id": portfolio_id,
        "pipeline_health": "ok" if not blockers else "incomplete",
        "blockers": blockers,
        "counts": {
            "portfolio_snapshots": portfolio_snaps,
            "latest_portfolio_snapshot": latest_ps.snapshot_date if latest_ps else None,
            "recommendation_snapshots": rec_snaps,
            "latest_recommendation_snapshot": (
                latest_rs.created_at.isoformat() + "Z"
                if latest_rs and latest_rs.created_at else None
            ),
            "execution_decisions": decisions_total,
            "approved_decisions": approved_decisions,
            "active_shadows": len(shadow_rows),
            "attribution_records": attribution_records,
            "regime_snapshots": regime_snaps,
            "benchmark_prices": benchmark_prices,
            "calibration_records": calibration_records,
        },
        "shadows": shadow_summary,
    }


@app.get("/analytics/decision-memory")
async def get_decision_memory_timeline(
    portfolio_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return an execution decision timeline for a portfolio.

    Each entry includes: decision type, timestamp, snapshot summary
    (persona, consensus, total value), and associated shadow portfolio
    performance summaries (if any exist).

    Ordered newest-first.  Max 50 rows.
    """
    ws = _ws_id(db)
    decisions = (
        db.query(UserExecutionDecision)
        .filter(
            UserExecutionDecision.workspace_id == ws,
            UserExecutionDecision.portfolio_id == portfolio_id,
        )
        .order_by(UserExecutionDecision.executed_at.desc())
        .limit(min(limit, 50))
        .all()
    )

    timeline = []
    for d in decisions:
        snap = db.query(RecommendationSnapshot).filter_by(
            id=d.recommendation_snapshot_id
        ).first()

        shadows = (
            db.query(ShadowPortfolio)
            .filter(
                (ShadowPortfolio.execution_decision_id == d.id) |
                (
                    (ShadowPortfolio.recommendation_snapshot_id == d.recommendation_snapshot_id) &
                    (ShadowPortfolio.portfolio_id == d.portfolio_id)
                )
            )
            .filter(ShadowPortfolio.workspace_id == ws)
            .all()
        )

        shadow_summaries = [
            {
                "shadow_id": s.id,
                "shadow_type": s.shadow_type,
                "name": s.name,
                "inception_date": s.inception_date,
                "inception_value": s.inception_value,
                "current_value": s.current_value,
                "inception_return_pct": s.inception_return_pct,
                "is_active": s.is_active,
                "last_valued_at": s.last_valued_at.isoformat() + "Z" if s.last_valued_at else None,
            }
            for s in shadows
        ]

        consensus = None
        regime = None
        if snap:
            if snap.consensus_json:
                try:
                    c = _json.loads(snap.consensus_json)
                    consensus = {
                        "consensus_type": c.get("consensus_type"),
                        "consensus_strength_score": c.get("consensus_strength_score"),
                        "consensus_decision": c.get("consensus_decision"),
                    }
                except Exception:
                    pass
            if snap.regime_snapshot_json:
                try:
                    r = _json.loads(snap.regime_snapshot_json)
                    regime = {"regime": r.get("regime"), "confidence_pct": r.get("confidence_pct")}
                except Exception:
                    pass

        timeline.append({
            "decision_id": d.id,
            "decision": d.decision,
            "portfolio_id": d.portfolio_id,
            "override_notes": d.override_notes,
            "override_type": d.override_type,
            "original_symbol": d.original_symbol,
            "replacement_symbol": d.replacement_symbol,
            "reason_category": d.reason_category,
            "executed_at": d.executed_at.isoformat() + "Z" if d.executed_at else None,
            "recommendation_snapshot": {
                "id": snap.id,
                "persona": snap.persona,
                "total_portfolio_value": snap.total_portfolio_value,
                "created_at": snap.created_at.isoformat() + "Z" if snap.created_at else None,
                "consensus": consensus,
                "regime": regime,
            } if snap else None,
            "shadows": shadow_summaries,
        })

    return timeline


@app.get("/analytics/confidence-history")
async def get_confidence_history(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return historical confidence calibration records for the workspace.

    Records are written automatically after each optimizer run.
    Ordered newest-first.  Max 50 rows.
    """
    ws = _ws_id(db)
    from models.database import ConfidenceCalibrationRecord

    rows = (
        db.query(ConfidenceCalibrationRecord)
        .filter_by(workspace_id=ws)
        .order_by(ConfidenceCalibrationRecord.computed_at.desc())
        .limit(min(limit, 50))
        .all()
    )

    return [
        {
            "id": r.id,
            "lookback_days": r.lookback_days,
            "calibration_score": r.calibration_score,
            "consensus_strength_calibration": r.consensus_strength_calibration,
            "policy_alignment_calibration": r.policy_alignment_calibration,
            "regime_confidence_calibration": r.regime_confidence_calibration,
            "optimizer_history_id": r.optimizer_history_id,
            "recommendation_snapshot_id": r.recommendation_snapshot_id,
            "computed_at": r.computed_at.isoformat() + "Z" if r.computed_at else None,
        }
        for r in rows
    ]


@app.get("/analytics/confidence-calibration")
async def get_confidence_calibration_v2(
    portfolio_id: int | None = None,
    lookback_days: int = 30,
    refresh: bool = False,
    db: Session = Depends(get_db),
) -> dict:
    """Enhanced confidence calibration with first-pass signal accuracy.

    Evaluates:
      1. Regime stability: were high-confidence regime calls stable?
      2. Signal directional accuracy: did BUY/ACCUMULATE signals go up?
         Grouped by confidence bucket (HIGH ≥70 / MEDIUM 40-69 / LOW <40)
      3. Policy compliance: stub — requires consecutive optimizer history.

    Set refresh=true to recompute (otherwise returns the latest stored record).
    Signals are evaluated only after ≥14 days (minimum holding period before
    an outcome is meaningful).
    """
    ws = _ws_id(db)
    from services.decision_memory.calibration import compute_calibration, get_latest_calibration

    if not refresh:
        latest = get_latest_calibration(db, ws)
        if latest:
            return {"source": "cached", "calibration": latest}

    result = await asyncio.to_thread(compute_calibration, db, ws, lookback_days)
    return {"source": "computed", "calibration": result}


# ─── Phase 3B.7C — Execution Lifecycle Endpoints ─────────────────────────────

@app.post("/optimizer/{snapshot_id}/decision")
async def record_decision_by_snapshot(
    snapshot_id: int,
    body: ExecutionDecisionRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Convenience endpoint — record an execution decision for a specific snapshot.

    Accepts snapshot_id from URL path; delegates to POST /optimizer/decisions.
    """
    body.recommendation_snapshot_id = snapshot_id
    return await record_execution_decision(body, db)


@app.get("/analytics/shadow-performance")
async def get_shadow_performance_summary(
    portfolio_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Portfolio-level shadow performance summary.

    Aggregates all active shadow portfolios for a portfolio into a single
    response with inception return, current value, last valued date, and
    benchmark alpha for each shadow type.  Null-safe for new portfolios.
    """
    ws = _ws_id(db)
    rows = (
        db.query(ShadowPortfolio)
        .filter_by(workspace_id=ws, portfolio_id=portfolio_id, is_active=True)
        .order_by(ShadowPortfolio.created_at.desc())
        .all()
    )
    if not rows:
        return {"portfolio_id": portfolio_id, "shadows": [], "has_shadows": False}

    from services.decision_memory.shadow_tracker import value_shadow_portfolio as _val_shadow

    shadows = []
    for s in rows:
        # Auto-repair: if inception_return_pct is clearly corrupted (< -99%),
        # re-trigger valuation with the stabilized engine so the DB row is fixed.
        if s.inception_return_pct is not None and s.inception_return_pct < -99.0:
            try:
                _val_shadow(db, s.id)
                db.refresh(s)
                _log.info("get_shadow_performance_summary: repaired shadow_id=%s (was %.2f%%)", s.id, s.inception_return_pct)
            except Exception as _rep_exc:
                _log.warning("get_shadow_performance_summary: repair failed shadow_id=%s: %s", s.id, _rep_exc)

        latest_snap = (
            db.query(ShadowPortfolioSnapshot)
            .filter_by(shadow_portfolio_id=s.id)
            .order_by(ShadowPortfolioSnapshot.snapshot_date.desc())
            .first()
        )

        # Apply plausibility guard before returning — never surface -100% to UI
        safe_return_pct = s.inception_return_pct
        if safe_return_pct is not None and (safe_return_pct < -99.9 or safe_return_pct > 1000.0):
            safe_return_pct = None

        shadows.append({
            "shadow_id": s.id,
            "shadow_type": s.shadow_type,
            "name": s.name,
            "inception_date": s.inception_date,
            "inception_value": s.inception_value,
            "current_value": s.current_value,
            "inception_return_pct": safe_return_pct,
            "last_valued_at": s.last_valued_at.isoformat() + "Z" if s.last_valued_at else None,
            "latest_alpha": latest_snap.alpha if latest_snap else None,
            "latest_benchmark_return_pct": latest_snap.benchmark_return_pct if latest_snap else None,
            "snapshot_count": (
                db.query(ShadowPortfolioSnapshot)
                .filter_by(shadow_portfolio_id=s.id)
                .count()
            ),
        })

    static = next((s for s in shadows if s["shadow_type"] == "STATIC_FROZEN"), None)
    active = next((s for s in shadows if s["shadow_type"] == "ACTIVE_MODEL"), None)

    return {
        "portfolio_id": portfolio_id,
        "has_shadows": True,
        "shadows": shadows,
        "summary": {
            "static_frozen": static,
            "active_model": active,
            "tracking_since": min(
                (s["inception_date"] for s in shadows if s["inception_date"]), default=None
            ),
        },
    }


@app.get("/analytics/ai-vs-human-timeline")
async def get_ai_vs_human_timeline(
    portfolio_id: int,
    evaluation_days: int = 90,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> dict:
    """Per-decision AI vs human performance timeline.

    Returns an ordered list of execution decisions each annotated with shadow
    return, actual return, and whether AI outperformed.  Null-safe: decisions
    without linked shadows are included with null deltas.
    Ordered newest-first, capped at min(limit, 50).
    """
    from services.analytics.human_vs_ai import compare_human_vs_ai

    try:
        comparison = await asyncio.to_thread(compare_human_vs_ai, db, portfolio_id, evaluation_days)
    except Exception as exc:
        _log.warning("ai_vs_human_timeline: compare failed: %s", exc)
        comparison = {"decisions": [], "summary": None}

    decisions = comparison.get("decisions", [])
    limited = decisions[:min(limit, 50)]

    return {
        "portfolio_id": portfolio_id,
        "evaluation_days": evaluation_days,
        "total_decisions": len(decisions),
        "timeline": limited,
        "summary": comparison.get("summary"),
    }


# ─── Phase 4C.4 — Human Idea Intake / AI Committee Review ────────────────────

class IdeaReviewRequest(BaseModel):
    symbols: list[str]


@app.post("/portfolios/{portfolio_id}/idea-review")
async def idea_review(
    portfolio_id: int,
    body: IdeaReviewRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Evaluate user-supplied stock ideas against the active portfolio's
    constraint envelope, persona, regime, and latest optimizer output.

    No AI calls — deterministic scoring over existing cached intelligence.
    Maximum 10 symbols per request.
    """
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.workspace_id == ws
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    from services.idea_review import review_ideas
    return await asyncio.to_thread(review_ideas, body.symbols, portfolio_id, db, ws)


# ─── Phase 4C.5A — Basket Simulation Engine ──────────────────────────────────

class BasketSimulationRequest(BaseModel):
    symbols: list[str]
    allocation_pct: float


@app.post("/portfolios/{portfolio_id}/basket-simulation")
async def basket_simulation(
    portfolio_id: int,
    body: BasketSimulationRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Simulate purchasing a basket of symbols against the active portfolio.

    No AI calls.  No trades executed.  Read-only deterministic analysis.
    Returns sector-level impacts, cash impact, warnings, and overall status.
    """
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.workspace_id == ws
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if body.allocation_pct <= 0 or body.allocation_pct > 100:
        raise HTTPException(status_code=422, detail="allocation_pct must be between 0 and 100")

    from services.basket_simulation import simulate_basket
    result = await asyncio.to_thread(
        simulate_basket, portfolio_id, body.symbols, body.allocation_pct, ws, db
    )
    return result.model_dump()


# ─── Phase 4C.5B — Portfolio Construction Assistant ───────────────────────────

class PortfolioConstructionRequest(BaseModel):
    symbols: list[str]


@app.post("/portfolios/{portfolio_id}/portfolio-construction")
async def portfolio_construction(
    portfolio_id: int,
    body: PortfolioConstructionRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Suggest the safest equal-weight allocation for a basket of symbols.

    Iterates from 5% down to 1% per position, returning the largest allocation
    that satisfies sector caps and cash-floor constraints.

    No AI calls.  No trades executed.  Read-only deterministic analysis.
    """
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.workspace_id == ws
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    from services.portfolio_construction import suggest_basket_allocation
    try:
        result = await asyncio.to_thread(
            suggest_basket_allocation, portfolio_id, body.symbols, ws, db
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result.model_dump()


# ─── Phase 4D.1 — Constraint-Aware Position Sizing ───────────────────────────

class PositionSizingRequest(BaseModel):
    symbols: list[str]
    timing_scores: dict[str, int] | None = None


@app.post("/portfolios/{portfolio_id}/position-sizing")
async def position_sizing(
    portfolio_id: int,
    body: PositionSizingRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Size a basket proportionally by signal quality, confidence, fit, and priority.

    Allocates deployable cash (cash − cash floor) across symbols in proportion
    to each symbol's position score.  Scales allocations downward when a sector
    cap would be breached.

    No AI calls.  No trades executed.  Read-only deterministic analysis.
    """
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.workspace_id == ws
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    from services.position_sizing import suggest_position_sizes
    try:
        result = await asyncio.to_thread(
            suggest_position_sizes, portfolio_id, body.symbols, ws, db, body.timing_scores
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result.model_dump()


# ─── Phase 4D.2 — Risk Budget Allocation ─────────────────────────────────────

class RiskBudgetRequest(BaseModel):
    symbols: list[str]


@app.post("/portfolios/{portfolio_id}/risk-budget-allocation")
async def risk_budget_allocation(
    portfolio_id: int,
    body: RiskBudgetRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Compute target portfolio weights using risk-adjusted allocation scoring.

    Scores each symbol by expected return (TA × 0.4 + FA × 0.4 + confidence × 0.2)
    divided by risk score, then normalises to 100 %.  Applies confidence filter,
    high-risk cap (5 %), max position cap (20 %), and sector concentration caps.

    No AI calls.  No trades executed.  Read-only deterministic analysis.
    """
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.workspace_id == ws
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    from services.allocation_engine import suggest_risk_budget
    try:
        result = await asyncio.to_thread(
            suggest_risk_budget, portfolio_id, body.symbols, ws, db
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result.model_dump()


# ─── Phase UX.2E — Execution Plan Generator ──────────────────────────────────

class ExecutionPlanRequest(BaseModel):
    buy_symbols: list[str]
    sizing_suggestions: list[dict] = []
    timing_scores: dict[str, int] | None = None


@app.post("/portfolios/{portfolio_id}/execution-plan")
async def execution_plan(
    portfolio_id: int,
    body: ExecutionPlanRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Build a ready-to-execute trade plan from existing analysis results.

    Identifies funding sources (SELL/REDUCE existing holdings) and sizes buy
    targets using the position sizing output.  No AI calls.  No mutations.
    """
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.workspace_id == ws
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    from services.execution_plan import build_execution_plan
    try:
        result = await asyncio.to_thread(
            build_execution_plan,
            portfolio_id, ws,
            body.buy_symbols, body.sizing_suggestions,
            body.timing_scores, db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result.model_dump()


# ─── Phase 4C.6F — Timing Intelligence Layer ─────────────────────────────────

class TimingIntelligenceRequest(BaseModel):
    symbols: list[str]


@app.post("/timing-intelligence")
async def timing_intelligence(body: TimingIntelligenceRequest) -> list[dict]:
    """Score entry timing for a basket of symbols using deterministic market signals.

    Computes a 0-100 timing score from four components:
        trend (40%)            — price vs SMA20/SMA50
        momentum (30%)         — RSI(14)
        relative_strength (20%) — 20-day excess return vs SPY
        volume (10%)           — current vs 20-day average volume

    No AI calls.  No database writes.  Read-only and reusable across the platform.
    """
    if not body.symbols:
        return []
    symbols = [s.strip().upper() for s in body.symbols if s.strip()]
    if not symbols:
        return []

    from services.timing_intelligence import score_timing_batch
    results = await asyncio.to_thread(score_timing_batch, symbols)
    return [r.model_dump() for r in results]


@app.get("/analytics/calibration-history")
async def get_calibration_history(
    portfolio_id: int | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Historical confidence calibration records, optionally filtered by portfolio.

    When portfolio_id is provided, filters records linked to that portfolio's
    recommendation snapshots.  Without it, returns workspace-wide records.
    Ordered newest-first.  Cap at min(limit, 100).
    """
    ws = _ws_id(db)
    q = (
        db.query(ConfidenceCalibrationRecord)
        .filter(ConfidenceCalibrationRecord.workspace_id == ws)
    )
    if portfolio_id:
        snapshot_ids = [
            r[0]
            for r in db.query(RecommendationSnapshot.id)
            .filter_by(workspace_id=ws, portfolio_id=portfolio_id)
            .all()
        ]
        if not snapshot_ids:
            return []
        q = q.filter(ConfidenceCalibrationRecord.recommendation_snapshot_id.in_(snapshot_ids))

    rows = q.order_by(ConfidenceCalibrationRecord.computed_at.desc()).limit(min(limit, 100)).all()

    return [
        {
            "id": r.id,
            "lookback_days": r.lookback_days,
            "calibration_score": r.calibration_score,
            "consensus_strength_calibration": r.consensus_strength_calibration,
            "policy_alignment_calibration": r.policy_alignment_calibration,
            "regime_confidence_calibration": r.regime_confidence_calibration,
            "optimizer_history_id": r.optimizer_history_id,
            "recommendation_snapshot_id": r.recommendation_snapshot_id,
            "computed_at": r.computed_at.isoformat() + "Z" if r.computed_at else None,
        }
        for r in rows
    ]


# ─── AI Evaluation M3 — Aggregation APIs & Verdict Composer ──────────────────
# See docs/AI_EVALUATION_IMPLEMENTATION_PLAN.md §5 M3. All endpoints here are
# read + in-memory aggregation only (grading itself stays in the scheduler,
# services/evaluation/horizon_grader.py + plan_grader.py, M1/M2) — every
# response carries as_of + a per-section/top-level status so the frontend
# (M4+) can render degraded/cold-start states instead of silent zeros
# (PLAN §4.7).

@app.get("/analytics/evaluation/scorecard")
async def get_evaluation_scorecard(
    portfolio_id: int,
    period_days: int = 90,
    db: Session = Depends(get_db),
) -> dict:
    """Three-lens (Belief / Execution / Outcome) aggregate for one portfolio.

    Reuses RecommendationGrade rows (M1 horizon grades, M2 plan grades) plus
    the existing compute_portfolio_attribution / compare_human_vs_ai
    analytics services — computes zero new grades. Cold-start portfolios
    (no optimizer run ever) return status="cold_start" with structured
    empty lenses, never zeros or an error.
    """
    _ws_id(db)
    from services.evaluation.scorecard import compute_scorecard

    return await asyncio.to_thread(compute_scorecard, db, portfolio_id, period_days)


@app.get("/analytics/evaluation/recommendations")
async def get_evaluation_recommendations_ledger(
    portfolio_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> dict:
    """Recommendations ledger (UX S2): every snapshot, newest first, with a
    per-horizon HorizonStrip (graded / maturing / pending_grading) and the
    decision recorded against it. Rejected/expired rows carry
    is_counterfactual=True — the recommendation-keyed shadow (P2) always
    exists regardless of what the human did.
    """
    _ws_id(db)
    from services.evaluation.recommendation_ledger import list_recommendations_ledger

    return await asyncio.to_thread(list_recommendations_ledger, db, portfolio_id, limit, offset)


@app.get("/analytics/evaluation/recommendations/{snapshot_id}")
async def get_evaluation_report_card(
    portfolio_id: int,
    snapshot_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Single-recommendation Report Card (UX S3): plan (day-0 PLAN grade) ->
    execution (plan-vs-actual, if a decision was recorded) -> outcome
    (horizon grades). Plan grading never changes; sections 2-3 fill in as
    reality arrives.
    """
    _ws_id(db)
    from services.evaluation.recommendation_ledger import get_report_card

    result = await asyncio.to_thread(get_report_card, db, portfolio_id, snapshot_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Recommendation snapshot not found")
    return result


@app.get("/analytics/evaluation/execution")
async def get_evaluation_execution_ledger(
    portfolio_id: int,
    period_days: int = 90,
    db: Session = Depends(get_db),
) -> dict:
    """Execution ledger (UX S4): decisions in the window with plan-vs-actual
    execution scores, plus class-segmented acceptance (UX D5 — never an
    unsegmented total).
    """
    _ws_id(db)
    from services.evaluation.execution_ledger import list_execution_ledger

    return await asyncio.to_thread(list_execution_ledger, db, portfolio_id, period_days)


@app.get("/analytics/evaluation/execution/{decision_id}")
async def get_evaluation_execution_detail(
    portfolio_id: int,
    decision_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Execution detail (UX S4b): per-symbol timing/size/funding deltas for
    one decision, plus the §8 PARTIAL-execution warning when applicable.
    """
    _ws_id(db)
    from services.evaluation.execution_ledger import get_execution_detail

    result = await asyncio.to_thread(get_execution_detail, db, portfolio_id, decision_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Execution decision not found")
    return result


# ─── Phase 4C.6A — Timing Intelligence: Allocation Periods ───────────────────

@app.get("/analytics/timing-periods")
async def get_timing_periods(
    portfolio_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Return all allocation periods for a portfolio.

    Each period spans from one RecommendationSnapshot becoming active to the
    moment the next snapshot replaced it.  The most-recent period is open-ended
    (end_date=null, is_current=true).

    Periods are sorted ascending by start_date and never overlap.
    """
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.workspace_id == ws
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    from services.timing_periods import build_allocation_periods

    periods = await asyncio.to_thread(build_allocation_periods, portfolio_id, ws, db)

    return {
        "portfolio_id": portfolio_id,
        "periods": [
            {
                "recommendation_snapshot_id": period.recommendation_snapshot_id,
                "start_date": period.start_date.isoformat().replace("+00:00", "Z"),
                "end_date": (
                    period.end_date.isoformat().replace("+00:00", "Z")
                    if period.end_date is not None
                    else None
                ),
                "days_active": period.days_active,
                "is_current": period.is_current,
            }
            for period in periods
        ],
    }


# ─── Phase 4C.6B — Timing Intelligence: Period Performance ───────────────────

@app.get("/analytics/timing-performance")
async def get_timing_performance(
    portfolio_id: int,
    benchmark: str = "^SET.BK",
    db: Session = Depends(get_db),
) -> dict:
    """Return per-allocation-period performance metrics for a portfolio.

    For each period (defined by when a RecommendationSnapshot became active),
    computes four deterministic metrics from PortfolioSnapshot and BenchmarkPrice:

        period_return_pct    — portfolio TWR over the period
        benchmark_return_pct — benchmark price return over same window
        excess_return_pct    — period_return_pct − benchmark_return_pct
        max_drawdown_pct     — peak-to-trough decline in portfolio total_value

    No AI calls.  No new tables.  Periods sorted ascending by start_date.
    """
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.workspace_id == ws
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    from services.timing_performance import build_period_performances

    performances = await asyncio.to_thread(
        build_period_performances, portfolio_id, ws, db, benchmark
    )

    return {
        "portfolio_id": portfolio_id,
        "benchmark": benchmark,
        "periods": [
            {
                "recommendation_snapshot_id": perf.recommendation_snapshot_id,
                "start_date": perf.start_date.isoformat().replace("+00:00", "Z"),
                "end_date": (
                    perf.end_date.isoformat().replace("+00:00", "Z")
                    if perf.end_date is not None
                    else None
                ),
                "days_active": perf.days_active,
                "is_current": perf.is_current,
                "period_return_pct": perf.period_return_pct,
                "benchmark_return_pct": perf.benchmark_return_pct,
                "excess_return_pct": perf.excess_return_pct,
                "max_drawdown_pct": perf.max_drawdown_pct,
                "snapshot_count": perf.snapshot_count,
            }
            for perf in performances
        ],
    }


# ─── Phase 4C.6C — Timing Intelligence: Timing Score ────────────────────────

@app.get("/analytics/timing-scores")
async def get_timing_scores(
    portfolio_id: int,
    benchmark: str = "^SET.BK",
    db: Session = Depends(get_db),
) -> dict:
    """Return a deterministic 0-100 timing quality score per allocation period.

    Scoring components (base 50):
        excess_return_component  excess_return_pct × 4, capped ±30
        drawdown_component       tiered bonus/penalty on max_drawdown_pct
        duration_component       stability bonus based on days_active

    Grade: EXCELLENT / GOOD / NEUTRAL / WEAK / POOR
    Confidence: HIGH / MEDIUM / LOW (based on snapshot_count)
    """
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.workspace_id == ws
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    from services.timing_performance import build_period_performances
    from services.timing_score import calculate_timing_score

    performances = await asyncio.to_thread(
        build_period_performances, portfolio_id, ws, db, benchmark
    )
    scored = [calculate_timing_score(perf) for perf in performances]

    scores = [s.timing_score for s in scored]
    average_score = round(sum(scores) / len(scores)) if scores else None

    return {
        "portfolio_id": portfolio_id,
        "benchmark": benchmark,
        "average_score": average_score,
        "best_score": max(scores) if scores else None,
        "worst_score": min(scores) if scores else None,
        "total_periods": len(scored),
        "periods": [
            {
                "recommendation_snapshot_id": s.recommendation_snapshot_id,
                "timing_score": s.timing_score,
                "timing_grade": s.timing_grade,
                "confidence_level": s.confidence_level,
                "excess_return_component": s.excess_return_component,
                "drawdown_component": s.drawdown_component,
                "duration_component": s.duration_component,
            }
            for s in scored
        ],
    }


# ─── Phase 4C.6D — Timing Intelligence: Regime Attribution ───────────────────

@app.get("/analytics/timing-regime-attribution")
async def get_timing_regime_attribution(
    portfolio_id: int,
    benchmark: str = "^SET.BK",
    db: Session = Depends(get_db),
) -> dict:
    """Return timing quality aggregated by market regime.

    Each period is assigned to the regime active on its start date
    (looked up from RegimeSnapshot history).  Regimes with no historical
    data before a period start are labelled UNKNOWN.

    Aggregate statistics per regime:
        average_score, best_score, worst_score
        average_excess_return_pct, average_drawdown_pct, average_duration_days

    Summary fields identify the best/worst regime by average timing score.
    """
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.workspace_id == ws
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    from services.regime_attribution import build_regime_attribution, build_summary

    results = await asyncio.to_thread(
        build_regime_attribution, portfolio_id, ws, db, benchmark
    )
    summary = build_summary(results)

    return {
        "portfolio_id": portfolio_id,
        "benchmark": benchmark,
        **summary,
        "regimes": [
            {
                "regime": r.regime,
                "periods": r.periods,
                "average_score": r.average_score,
                "best_score": r.best_score,
                "worst_score": r.worst_score,
                "average_excess_return_pct": r.average_excess_return_pct,
                "average_drawdown_pct": r.average_drawdown_pct,
                "average_duration_days": r.average_duration_days,
            }
            for r in results
        ],
    }


# ─── Phase 4C.6E — Timing Intelligence: Human vs AI Timing Attribution ───────

@app.get("/analytics/human-vs-ai-timing")
async def get_human_vs_ai_timing(
    portfolio_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Attribute portfolio outcomes to human override decisions vs AI recommendations.

    For each UserExecutionDecision linked to an allocation period:
      - REJECTED / MANUAL_OVERRIDE / PARTIAL_EXECUTION → override = True
      - APPROVED                                        → override = False

    Compares actual portfolio return (human) vs STATIC_FROZEN shadow return (AI)
    within the allocation period window.

    delta_return_pct = human_return - ai_return
      positive → human outperformed AI  → GOOD_OVERRIDE
      negative → AI outperformed human  → BAD_OVERRIDE
      |delta| < 0.25                   → NEUTRAL_OVERRIDE
    """
    ws = _ws_id(db)
    p = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.workspace_id == ws
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    from services.human_vs_ai_timing import build_human_vs_ai_timing

    attributions, summary = await asyncio.to_thread(
        build_human_vs_ai_timing, portfolio_id, ws, db
    )

    return {
        "portfolio_id": portfolio_id,
        "summary": {
            "overrides": summary.overrides,
            "good_overrides": summary.good_overrides,
            "bad_overrides": summary.bad_overrides,
            "neutral_overrides": summary.neutral_overrides,
            "override_win_rate": summary.override_win_rate,
            "total_added_return_pct": summary.total_added_return_pct,
            "total_saved_drawdown_pct": summary.total_saved_drawdown_pct,
            "override_type_counts": summary.override_type_counts,
            "override_type_win_rates": summary.override_type_win_rates,
        },
        "details": [
            {
                "recommendation_snapshot_id": a.recommendation_snapshot_id,
                "symbol": a.symbol,
                "ai_action": a.ai_action,
                "human_action": a.human_action,
                "override": a.override,
                "override_type": a.override_type,
                "human_return_pct": a.human_return_pct,
                "ai_return_pct": a.ai_return_pct,
                "delta_return_pct": a.delta_return_pct,
                "human_drawdown_pct": a.human_drawdown_pct,
                "ai_drawdown_pct": a.ai_drawdown_pct,
                "saved_drawdown_pct": a.saved_drawdown_pct,
                "outcome": a.outcome,
            }
            for a in attributions
        ],
    }
