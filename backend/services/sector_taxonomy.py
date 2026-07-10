"""Sector classification — static taxonomy (Classification Consolidation).

This module used to live inline in main.py. It has not been redesigned by
the Classification Consolidation milestone (docs/implementation/
CLASSIFICATION_CONSOLIDATION.md) — the maps and rules below are byte-for-byte
what main.py contained before, moved here unchanged so they can be shared by
two consumers that must not import main.py itself (a FastAPI app module with
route-registration side effects):

  1. main.py's _get_sector() / _fetch_sector() — which now consult the Asset
     Registry (services/registry_lookup.py) FIRST, and fall back to the maps
     here only when the Registry has no current SECTOR classification for
     that symbol.
  2. services/registry_classification_seed.py — the one-time seed that
     copies these maps' values into the Registry as SECTOR classification
     facts, so the Registry can answer (1) without a network call once an
     asset has been seeded.

These maps are therefore no longer *the* authority — the Registry is
(ASSET_REGISTRY.md Section 8: "Registry describes; Portfolio Policy
judges" — applied here as "Registry classifies; this module seeds and
falls back"). They remain the only classification source for any symbol
the Registry has not yet resolved or has resolved but not yet classified
(M5 Track B / M6 Native Integration is what eventually gives every symbol
a Registry-native identity; until then, partial coverage is expected and
this fallback is load-bearing, not vestigial).
"""
from __future__ import annotations

import re

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


def dr_prefix(symbol: str) -> str | None:
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


def static_sector_lookup(symbol: str, *, is_dr: bool) -> str | None:
    """Network-free lookup against the static maps only — no FA cache, no
    Registry. Returns None (never "Other") when the maps have no entry, so
    callers can distinguish "no seed data available" from "classified as
    Other" and chain further fallbacks accordingly.

    `is_dr` must be pre-computed by the caller (services.data_fetcher's
    normalize_dr_symbol(symbol) != symbol) — this module never calls
    yfinance-adjacent code, keeping it a pure, dependency-free source of
    seed data for both main.py and the Registry classification seed.
    """
    if is_dr:
        prefix = dr_prefix(symbol)
        return _DR_SECTOR_MAP.get(prefix) if prefix else None
    if symbol.endswith(".BK"):
        return THAI_SECTOR_MAP.get(symbol)
    return None
