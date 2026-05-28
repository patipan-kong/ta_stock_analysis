"""Runtime environment detection for Hybrid Research Architecture.

Environment roles
─────────────────
  APP_ENV=local  (default)
      Research / ETL / Market Data Ingestion Node.
      May access yfinance, run schedulers, background refresh loops.

  APP_ENV=vps
      Read-only Dashboard + API Serving Layer.
      NEVER triggers yfinance, schedulers, or background refresh workers.
      Serves cached / pre-computed DB-only responses.

Usage
─────
    from services.core.runtime_env import allow_market_fetching, require_local_env

    # Guard at fetch entry-points:
    if not allow_market_fetching():
        log.warning("[VPS BLOCKED FETCH] symbol=%s", symbol)
        return None          # caller falls through to stale cache

    # Raise if a function must never run on VPS:
    require_local_env("setup_scheduler")
"""
from __future__ import annotations

import logging
import os

_log = logging.getLogger(__name__)

# ── Role constants ─────────────────────────────────────────────────────────────
_ENV_LOCAL = "local"
_ENV_VPS   = "vps"


def _app_env() -> str:
    """Return the normalised APP_ENV string (lowercase, stripped)."""
    return os.environ.get("APP_ENV", _ENV_LOCAL).strip().lower()


# ── Public predicates ──────────────────────────────────────────────────────────

def is_local_env() -> bool:
    """True when running on the local Research / ETL node."""
    return _app_env() == _ENV_LOCAL


def is_vps_env() -> bool:
    """True when running on the VPS Dashboard / API serving layer."""
    return _app_env() == _ENV_VPS


def allow_market_fetching() -> bool:
    """True only on LOCAL.  VPS must never trigger live market data calls."""
    allowed = is_local_env()
    if not allowed:
        _log.info(
            "[VPS BLOCKED FETCH] Live market fetch suppressed (APP_ENV=%s). "
            "Falling back to DB cache.",
            _app_env(),
        )
    return allowed


# ── Enforcement helper ─────────────────────────────────────────────────────────

def require_local_env(caller: str = "") -> None:
    """Raise RuntimeError if called from VPS context.

    Use this to hard-block scheduler / cron startup on VPS.
    """
    if not is_local_env():
        raise RuntimeError(
            f"[VPS BLOCKED] '{caller}' must not run on VPS (APP_ENV={_app_env()}). "
            "This operation is reserved for the local Research Node."
        )


# ── System status dict (exposed by /system/status endpoint) ───────────────────

def get_system_status() -> dict:
    """Return a JSON-safe dict describing the current runtime role."""
    env = _app_env()
    return {
        "app_env":                   env,
        "role":                      "Research Node" if env == _ENV_LOCAL else "Cloud Dashboard",
        "read_only_market_data":     env == _ENV_VPS,
        "scheduler_enabled":         env == _ENV_LOCAL,
        "live_fetch_enabled":        env == _ENV_LOCAL,
        "description": (
            "Local Research Engine — live market data, schedulers, and analytics active."
            if env == _ENV_LOCAL
            else "Cloud Dashboard Mode — market data synced from Local Research Node. "
                 "Live fetching disabled; serving cached DB responses."
        ),
    }
