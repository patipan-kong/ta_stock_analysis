"""Tests for the Listing Equivalence Rule (Milestone M5.0).

Validates:
  1. Identical strings never "bundle" (nothing to decide)
  2. Venue-suffix-only divergence (KBANK / KBANK.BK) is bundleable
  3. DR-mapped divergence (explicit YFINANCE_SYMBOL_MAP entries) is never
     bundleable, even though the pair superficially "looks like" a
     suffix relationship
  4. DR-mapped divergence via the generic suffix-stripping regex
     (NVDA01 -> NVDA) is never bundleable — the trickiest case, since it
     resembles the safe KBANK/KBANK.BK pattern but is actually a
     DR-to-underlying substitution
  5. None/empty inputs never bundle
  6. Non-DR, non-suffix divergence (unclassified) never bundles

Pure function; no database, no I/O.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.listing_equivalence import same_listing


def test_identical_strings_do_not_bundle():
    assert same_listing("AAPL", "AAPL") is False
    assert same_listing("KBANK.BK", "KBANK.BK") is False


def test_venue_suffix_only_divergence_bundles():
    assert same_listing("KBANK", "KBANK.BK") is True
    assert same_listing("PTT", "PTT.BK") is True
    assert same_listing("AOT", "AOT.BK") is True


def test_explicit_dr_map_divergence_never_bundles():
    # CATL01 -> 300750.SZ (Shenzhen underlying) via YFINANCE_SYMBOL_MAP.
    # Superficially just "a different string", but is_dr() correctly
    # vetoes it: this is a DR wrapping a foreign underlying, not a
    # respelling of one listing (ASSET_REGISTRY.md Section 5).
    assert same_listing("CATL01", "300750.SZ") is False
    assert same_listing("MICRON01", "MU") is False
    assert same_listing("SMIC01", "0981.HK") is False


def test_generic_dr_suffix_stripping_never_bundles():
    # NVDA01 -> NVDA looks exactly like the KBANK/KBANK.BK shape (base
    # ticker plus a stripped suffix) but is a DR-to-underlying mapping,
    # not a venue-suffix convention. This is the case the Listing
    # Equivalence Rule exists specifically to catch.
    assert same_listing("NVDA01", "NVDA") is False
    assert same_listing("NVDA01.BK", "NVDA") is False


def test_none_and_empty_inputs_never_bundle():
    assert same_listing(None, "KBANK.BK") is False
    assert same_listing("KBANK", None) is False
    assert same_listing(None, None) is False
    assert same_listing("", "") is False


def test_unclassified_divergence_defaults_to_no_bundle():
    # Neither a venue-suffix pattern nor a DR pattern — the rule must
    # fail toward surfacing ambiguity, never guess (ASSET_REGISTRY.md
    # Section 4).
    assert same_listing("0700", "0700.HK") is False
    assert same_listing("BABA", "9988.HK") is False
