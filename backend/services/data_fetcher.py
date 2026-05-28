"""Cache-aware market data facade.

Call hierarchy:
  agents / main.py
      ↓  fetch_history / fetch_info / fetch_price_info / fetch_news
  data_fetcher  ← this module (cache layer)
      ↓  on cache-miss or cache-expired
  services.market_data.YahooProvider (network I/O)
      ↓  on failure
  stale cache (served with _stale_data metadata attached)

TTL policy:
  quote             → 5 min
  history intraday  → 5 min
  history short     → 15 min (1mo / 3mo)
  history long      → 24 h  (6mo+ / weekly)
  fundamental/info  → 24 h
  benchmark         → 15 min
"""
from __future__ import annotations

import io
import json as _json
import logging
import re
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from models.database import MarketDataCache, SessionLocal
from services.core.runtime_env import allow_market_fetching
from services.market_data.yahoo import YahooProvider, _is_rate_limit

_log = logging.getLogger(__name__)

# ── DR symbol regex ────────────────────────────────────────────────────────────
_DR_RE = re.compile(r"^([A-Z]+)\d{2}\.BK$")

# ── Provider singleton ─────────────────────────────────────────────────────────
_provider: YahooProvider = YahooProvider()

# ── TTL table (seconds) ────────────────────────────────────────────────────────
_TTL_QUOTE       = 5  * 60        # 5 min  – live prices
_TTL_FUND        = 24 * 3600      # 24 h   – P/E, ROE, sector, …
_TTL_BENCHMARK   = 15 * 60        # 15 min – index / ETF prices
_TTL_HIST_INTRA  = 5  * 60        # 5 min  – intraday bars
_TTL_HIST_SHORT  = 15 * 60        # 15 min – 1mo / 3mo daily
_TTL_HIST_LONG   = 24 * 3600      # 24 h   – 6mo+ / weekly


def _history_ttl(period: str, interval: str) -> int:
    if interval in ("1m", "2m", "5m", "15m", "30m", "60m", "1h"):
        return _TTL_HIST_INTRA
    if period in ("1d", "5d"):
        return _TTL_HIST_INTRA
    if period in ("1mo", "3mo"):
        return _TTL_HIST_SHORT
    return _TTL_HIST_LONG


# ── In-process stats counters (reset on server restart) ───────────────────────
_stats_lock = threading.Lock()
_stats: dict = {
    "cache_hits":              0,
    "cache_misses":            0,
    "stale_served":            0,
    "yahoo_requests":          0,
    "yahoo_errors":            0,
    "timeouts":                0,
    "rate_limits":             0,
    "yahoo_total_latency_ms":  0.0,
    "yahoo_latency_samples":   0,
    "started_at":              datetime.utcnow().isoformat() + "Z",
}


def _inc(key: str, amount: float = 1.0) -> None:
    with _stats_lock:
        _stats[key] = _stats.get(key, 0) + amount


def get_cache_stats() -> dict:
    """Return a copy of current in-process counters (used by /admin/cache-stats)."""
    with _stats_lock:
        s = dict(_stats)
    total = s["cache_hits"] + s["cache_misses"]
    hit_rate  = round(s["cache_hits"]  / total * 100, 1) if total else 0.0
    miss_rate = round(100 - hit_rate, 1) if total else 0.0
    avg_lat   = (
        round(s["yahoo_total_latency_ms"] / s["yahoo_latency_samples"], 1)
        if s["yahoo_latency_samples"] else 0.0
    )
    # Extrapolate to a per-day request rate
    started = datetime.fromisoformat(s["started_at"].rstrip("Z"))
    uptime_h = (datetime.utcnow() - started).total_seconds() / 3600
    req_per_day = round(s["yahoo_requests"] / uptime_h * 24, 0) if uptime_h > 0 else 0

    return {
        **s,
        "hit_rate_pct":              hit_rate,
        "miss_rate_pct":             miss_rate,
        "avg_yahoo_latency_ms":      avg_lat,
        "yahoo_requests_per_day_est": req_per_day,
        "uptime_hours":              round(uptime_h, 2),
    }


# ── Cache I/O helpers ──────────────────────────────────────────────────────────

def _get_cached(symbol: str, cache_type: str) -> Optional[dict]:
    """Return valid (non-expired) cached payload or None."""
    db = SessionLocal()
    try:
        entry: MarketDataCache | None = (
            db.query(MarketDataCache)
            .filter_by(symbol=symbol, cache_type=cache_type)
            .first()
        )
        if entry is None:
            _log.debug("cache_miss symbol=%s type=%s", symbol, cache_type)
            _inc("cache_misses")
            return None
        if entry.expires_at < datetime.utcnow():
            _log.debug("cache_expired symbol=%s type=%s", symbol, cache_type)
            _inc("cache_misses")
            return None
        entry.hit_count = (entry.hit_count or 0) + 1
        db.commit()
        _log.debug("cache_hit symbol=%s type=%s", symbol, cache_type)
        _inc("cache_hits")
        return _json.loads(entry.payload_json)
    except Exception as exc:
        _log.warning("cache_read_error symbol=%s type=%s: %s", symbol, cache_type, exc)
        return None
    finally:
        db.close()


def _set_cached(symbol: str, cache_type: str, payload: dict, ttl_secs: int) -> None:
    now     = datetime.utcnow()
    expires = now + timedelta(seconds=ttl_secs)
    payload_str = _json.dumps(payload, default=str)
    db = SessionLocal()
    try:
        entry = (
            db.query(MarketDataCache)
            .filter_by(symbol=symbol, cache_type=cache_type)
            .first()
        )
        if entry:
            entry.payload_json = payload_str
            entry.fetched_at   = now
            entry.expires_at   = expires
        else:
            db.add(MarketDataCache(
                symbol=symbol, cache_type=cache_type,
                payload_json=payload_str,
                fetched_at=now, expires_at=expires,
                hit_count=0,
            ))
        db.commit()
    except Exception as exc:
        _log.warning("cache_write_error symbol=%s type=%s: %s", symbol, cache_type, exc)
        db.rollback()
    finally:
        db.close()


def _get_stale(symbol: str, cache_type: str) -> Optional[dict]:
    """Return an expired cache entry as a stale fallback (includes _stale_data metadata)."""
    db = SessionLocal()
    try:
        entry = (
            db.query(MarketDataCache)
            .filter_by(symbol=symbol, cache_type=cache_type)
            .first()
        )
        if entry is None:
            return None
        payload = _json.loads(entry.payload_json)
        age_s   = (datetime.utcnow() - entry.fetched_at).total_seconds()
        payload["_stale_data"]         = True
        payload["_cache_age_minutes"]  = round(age_s / 60, 1)
        _inc("stale_served")
        _log.warning(
            "stale_cache_served symbol=%s type=%s age_min=%.1f",
            symbol, cache_type, age_s / 60,
        )
        return payload
    except Exception:
        return None
    finally:
        db.close()


# ── DataFrame serialisation ────────────────────────────────────────────────────

def _df_to_payload(df: pd.DataFrame) -> dict:
    try:
        return {"json_split": df.to_json(orient="split", date_format="iso", default_handler=str)}
    except Exception as exc:
        _log.error("df_serialize_error: %s", exc)
        return {}


def _payload_to_df(payload: dict) -> Optional[pd.DataFrame]:
    if not payload or "json_split" not in payload:
        return None
    try:
        df = pd.read_json(io.StringIO(payload["json_split"]), orient="split")
        df.index = pd.to_datetime(df.index, utc=True)
        return df
    except Exception as exc:
        _log.error("df_deserialize_error: %s", exc)
        return None


# ── DR / symbol helpers (public, consumed by agents and main.py) ───────────────

def normalize_dr_symbol(symbol: str) -> str:
    """Strip DR digit-suffix so yfinance can find the underlying US company.

    AAPL01.BK → 'AAPL'   (DR → base ticker)
    PTT.BK    → 'PTT.BK' (unchanged – regular Thai stock)
    AAPL      → 'AAPL'   (unchanged – US ticker)
    """
    m = _DR_RE.match(symbol)
    return m.group(1) if m else symbol


def is_dr_symbol(symbol: str) -> bool:
    return bool(_DR_RE.match(symbol))


def resolve_symbol(symbol: str) -> str:
    symbol = symbol.upper()
    if symbol.endswith(".BK"):
        return symbol
    return symbol


# ── Internal fetch helpers ─────────────────────────────────────────────────────

def _record_yf_call(t0: float) -> None:
    elapsed_ms = (time.monotonic() - t0) * 1000
    _inc("yahoo_total_latency_ms", elapsed_ms)
    _inc("yahoo_latency_samples")
    _log.info("yahoo_fetch_time latency_ms=%.0f", elapsed_ms)


def _record_yf_error(e: Exception) -> None:
    _inc("yahoo_errors")
    if _is_rate_limit(e):
        _inc("rate_limits")
        _log.warning("yahoo_rate_limit: %s", e)
    else:
        _log.error("yahoo_fetch_error: %s", e)


# ── Public API (same signatures as the original data_fetcher.py) ───────────────

def fetch_history(symbol: str, period: str = "6mo", interval: str = "1d") -> Optional[pd.DataFrame]:
    cache_type = f"history:{period}:{interval}"
    ttl        = _history_ttl(period, interval)

    cached = _get_cached(symbol, cache_type)
    if cached:
        return _payload_to_df(cached)

    if not allow_market_fetching():
        _log.info("[VPS BLOCKED FETCH] fetch_history symbol=%s — returning stale cache", symbol)
        stale = _get_stale(symbol, cache_type)
        return _payload_to_df(stale) if stale else None

    _inc("yahoo_requests")
    t0 = time.monotonic()
    try:
        df = _provider.get_history(symbol, period, interval)
        _record_yf_call(t0)
        _log.info("[LOCAL FETCH] yahoo_fetch symbol=%s type=%s", symbol, cache_type)
        if df is not None and not df.empty:
            _set_cached(symbol, cache_type, _df_to_payload(df), ttl)
        return df
    except Exception as exc:
        _record_yf_error(exc)
        stale = _get_stale(symbol, cache_type)
        return _payload_to_df(stale) if stale else None


def fetch_info(symbol: str) -> dict:
    """Fetch yfinance .info for a symbol.
    Callers are responsible for normalising DR symbols via normalize_dr_symbol() first."""
    cache_type = "fundamental"

    cached = _get_cached(symbol, cache_type)
    if cached:
        return {k: v for k, v in cached.items() if not k.startswith("_")}

    if not allow_market_fetching():
        _log.info("[VPS BLOCKED FETCH] fetch_info symbol=%s — returning stale cache", symbol)
        stale = _get_stale(symbol, cache_type)
        if stale:
            return {k: v for k, v in stale.items() if not k.startswith("_")}
        return {}

    _inc("yahoo_requests")
    t0 = time.monotonic()
    try:
        info = _provider.get_fundamentals(symbol)
        _record_yf_call(t0)
        _log.info("[LOCAL FETCH] yahoo_fetch symbol=%s type=fundamental", symbol)
        if info:
            _set_cached(symbol, cache_type, info, _TTL_FUND)
        return info or {}
    except Exception as exc:
        _record_yf_error(exc)
        stale = _get_stale(symbol, cache_type)
        if stale:
            return {k: v for k, v in stale.items() if not k.startswith("_")}
        return {}


def fetch_price_info(symbol: str) -> dict:
    """Return {current_price, change_percent, last_updated} for a symbol."""
    cache_type = "quote"

    cached = _get_cached(symbol, cache_type)
    if cached:
        return {k: v for k, v in cached.items() if not k.startswith("_")}

    if not allow_market_fetching():
        _log.info("[VPS BLOCKED FETCH] fetch_price_info symbol=%s — returning stale cache", symbol)
        stale = _get_stale(symbol, cache_type)
        if stale:
            return {k: v for k, v in stale.items() if not k.startswith("_")}
        return {"current_price": None, "change_percent": None, "last_updated": None, "_vps_cache_miss": True}

    _inc("yahoo_requests")
    t0 = time.monotonic()
    try:
        result = _provider.get_quote(symbol)
        _record_yf_call(t0)
        _log.info("[LOCAL FETCH] yahoo_fetch symbol=%s type=quote", symbol)
        if result.get("current_price") is not None:
            _set_cached(symbol, cache_type, result, _TTL_QUOTE)
        return result
    except Exception as exc:
        _record_yf_error(exc)
        stale = _get_stale(symbol, cache_type)
        if stale:
            return {k: v for k, v in stale.items() if not k.startswith("_")}
        return {"current_price": None, "change_percent": None, "last_updated": None}


def fetch_news(symbol: str) -> list[dict]:
    """Callers are responsible for normalising DR symbols via normalize_dr_symbol() first."""
    if not allow_market_fetching():
        _log.info("[VPS BLOCKED FETCH] fetch_news symbol=%s — returning empty list", symbol)
        return []

    # News is short-lived and already managed by AgentCache (1 h TTL).
    _inc("yahoo_requests")
    t0 = time.monotonic()
    try:
        result = _provider.get_news(symbol)
        _record_yf_call(t0)
        _log.info("[LOCAL FETCH] yahoo_fetch symbol=%s type=news", symbol)
        return result
    except Exception as exc:
        _record_yf_error(exc)
        return []


def prefetch_history_batch(
    symbols: list[str], period: str = "6mo", interval: str = "1d"
) -> None:
    """Warm the cache for a batch of symbols using yf.download() in chunks.

    Call this before a concurrent analysis burst to replace N individual
    yfinance requests with ceil(N/15) batched downloads.
    Only fetches symbols whose cache entry is missing or expired.
    Silently skips on VPS — the cache was pre-warmed by the Local Research Node.
    """
    if not allow_market_fetching():
        _log.info("[VPS BLOCKED FETCH] prefetch_history_batch — skipped on VPS")
        return

    cache_type = f"history:{period}:{interval}"
    ttl        = _history_ttl(period, interval)

    stale = [s for s in symbols if _get_cached(s, cache_type) is None]
    if not stale:
        return

    _log.info("[LOCAL FETCH] prefetch_history_batch symbols=%d period=%s interval=%s", len(stale), period, interval)
    _inc("yahoo_requests", len(stale))
    t0 = time.monotonic()
    try:
        batch = _provider.get_history_batch(stale, period, interval)
        _record_yf_call(t0)
        for sym, df in batch.items():
            if df is not None and not df.empty:
                _set_cached(sym, cache_type, _df_to_payload(df), ttl)
    except Exception as exc:
        _record_yf_error(exc)
