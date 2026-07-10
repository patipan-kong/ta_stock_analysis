"""services/sector_taxonomy.py — regression tests for the static sector
taxonomy extracted from main.py during Classification Consolidation
(docs/implementation/CLASSIFICATION_CONSOLIDATION.md).

These prove the extraction was behavior-preserving: static_sector_lookup()
must return exactly what main.py's old inline _get_sector() logic computed
for the same inputs, for every category the extraction is required to keep
identical (Thai equities, DR/US equities, unmapped symbols, non-canonical
raw sector strings).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.sector_taxonomy import (
    THAI_SECTOR_MAP,
    _DR_SECTOR_MAP,
    dr_prefix,
    normalize_sector,
    static_sector_lookup,
)


# ── Thai equities ────────────────────────────────────────────────────────

def test_thai_equity_resolves_from_thai_sector_map():
    assert static_sector_lookup("KBANK.BK", is_dr=False) == "Financial"
    assert static_sector_lookup("PTT.BK", is_dr=False) == "Energy"


def test_thai_equity_not_in_map_returns_none_not_other():
    assert static_sector_lookup("ZZZZ.BK", is_dr=False) is None


# ── DR / US equities ─────────────────────────────────────────────────────

def test_dr_symbol_resolves_from_dr_sector_map_via_prefix():
    assert static_sector_lookup("NVDA01.BK", is_dr=True) == "Technology"
    assert static_sector_lookup("TSLA05.BK", is_dr=True) == "Consumer"


def test_dr_symbol_not_in_map_returns_none():
    assert static_sector_lookup("UNKNOWNDR99.BK", is_dr=True) is None


def test_bare_us_symbol_is_not_a_dr_and_not_bk_returns_none():
    # US-listed symbol with no local DR wrapper and no .BK suffix — the
    # static maps have nothing to say; caller (main.py) falls through to
    # the FA cache.
    assert static_sector_lookup("AAPL", is_dr=False) is None


def test_dr_prefix_requires_two_trailing_digits():
    assert dr_prefix("NVDA01.BK") == "NVDA"
    assert dr_prefix("MICRON01") == "MICRON"
    # Single trailing digit (Thai tickers like PR9.BK, COM7.BK) must never
    # be mistaken for a DR prefix.
    assert dr_prefix("PR9.BK") is None
    assert dr_prefix("COM7.BK") is None


# ── ETFs (no static sector data — fall through by design) ──────────────

def test_etf_symbol_with_no_static_entry_returns_none():
    # ETFs are not present in either static map (asset_type, not sector, is
    # the classifying fact for them) — static_sector_lookup honestly
    # reports "no data" rather than guessing.
    assert static_sector_lookup("SPY", is_dr=False) is None


# ── normalize_sector: raw string canonicalization ───────────────────────

def test_normalize_sector_passes_through_canonical_values():
    assert normalize_sector("Technology") == "Technology"
    assert normalize_sector("Other") == "Other"


def test_normalize_sector_buckets_known_substrings():
    assert normalize_sector("Financial Services") == "Financial"
    assert normalize_sector("Consumer Cyclical") == "Consumer"
    assert normalize_sector("Consumer Defensive") == "Consumer"
    assert normalize_sector("Industrials") == "Industrial"


def test_normalize_sector_unmapped_raw_string_returns_other():
    assert normalize_sector("Basic Materials") == "Other"
    assert normalize_sector("Communication Services") == "Other"
    assert normalize_sector(None) == "Other"
    assert normalize_sector("") == "Other"


# ── Data integrity: every map value is canonical ────────────────────────

def test_every_thai_sector_map_value_is_a_dict_of_known_sectors():
    from services.sector_taxonomy import _CANONICAL_SECTORS
    for symbol, sector in THAI_SECTOR_MAP.items():
        assert sector in _CANONICAL_SECTORS, f"{symbol} -> {sector!r} is not canonical"


def test_every_dr_sector_map_value_is_canonical():
    from services.sector_taxonomy import _CANONICAL_SECTORS
    for prefix, sector in _DR_SECTOR_MAP.items():
        assert sector in _CANONICAL_SECTORS, f"{prefix} -> {sector!r} is not canonical"
