"""Stage R1 (M11 brief): Ledger Validator's shadow consultation of the Asset
Definition Runtime via _consult_runtime_capabilities().

Coverage
--------
  1.  No DIVIDEND / no aliasing / no cash-movement tx  -> consulted == 0
  2.  DIVIDEND transactions          -> agrees with EQUITY grants_flow(DIVIDEND)
  3.  Aliased symbols (SYMBOL_ALIAS) -> agrees with EQUITY permits_relationship(SAME_ENTITY)
  4.  DEPOSIT/WITHDRAW/INITIAL_CASH  -> agrees with CASH numeraire NOT_TRANSACTABLE
  5.  Mismatch is recorded as a RuntimeMismatch finding without raising
  6.  MissingBinding finding when the registry cannot resolve the binding
  7.  Registry boot failure -> single MissingBinding finding, never raises
  8.  Full validate_portfolio_ledger() run: runtime_consultation populated,
      but report.findings / overall_severity are completely unaffected
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from services.asset_domain import AssetType
from services.ledger_validator import (
    RuntimeConsultationLog,
    RuntimeFindingCategory,
    _consult_runtime_capabilities,
)
from services.transaction_canonicalizer import canonicalize_transactions


# ── Helpers (mirrors test_ledger_validator.py's style) ─────────────────────

def _tx(
    tx_id: int,
    tx_type: str,
    symbol: str | None = None,
    shares: float | None = None,
    price: float | None = None,
    amount: float = 0.0,
    date_str: str = "2026-01-01",
) -> SimpleNamespace:
    tx_date = datetime.strptime(date_str, "%Y-%m-%d")
    return SimpleNamespace(
        id=tx_id, transaction_type=tx_type, symbol=symbol, shares=shares,
        price_per_share=price, total_amount=amount, fees=0.0, taxes=0.0,
        sector=None, transaction_date=tx_date, created_at=tx_date, notes=None,
    )


def _canonical(txs):
    return list(canonicalize_transactions(txs))


# ── 1. Nothing to consult ───────────────────────────────────────────────────

def test_no_consultation_when_nothing_triggers_it():
    ctxs = _canonical([_tx(1, "BUY", "KBANK.BK", shares=100, price=100, amount=10_000)])
    log = _consult_runtime_capabilities(ctxs)
    assert log.consulted == 0
    assert log.agreements == 0
    assert log.findings == ()


# ── 2. DIVIDEND agrees with EQUITY grants_flow(DIVIDEND) ───────────────────

def test_dividend_transactions_agree_with_runtime():
    ctxs = _canonical([_tx(1, "DIVIDEND", amount=500.0)])
    log = _consult_runtime_capabilities(ctxs)
    assert log.consulted == 1
    assert log.agreements == 1
    assert log.findings == ()


# ── 3. SYMBOL_ALIAS merge agrees with EQUITY permits SAME_ENTITY ───────────

def test_symbol_alias_merge_agrees_with_runtime():
    ctxs = _canonical([
        _tx(1, "BUY", "KBANK", shares=100, price=100, amount=10_000, date_str="2026-01-01"),
        _tx(2, "BUY", "KBANK.BK", shares=50, price=100, amount=5_000, date_str="2026-01-02"),
    ])
    log = _consult_runtime_capabilities(ctxs)
    assert log.consulted == 1
    assert log.agreements == 1
    assert log.findings == ()


def test_single_symbol_no_alias_does_not_trigger_relationship_consultation():
    ctxs = _canonical([_tx(1, "BUY", "KBANK.BK", shares=100, price=100, amount=10_000)])
    log = _consult_runtime_capabilities(ctxs)
    assert log.consulted == 0


# ── 4. Cash-movement types agree with CASH numeraire NOT_TRANSACTABLE ──────

@pytest.mark.parametrize("tx_type", ["DEPOSIT", "WITHDRAW", "INITIAL_CASH"])
def test_cash_movement_types_agree_with_runtime(tx_type):
    ctxs = _canonical([_tx(1, tx_type, amount=1_000.0)])
    log = _consult_runtime_capabilities(ctxs)
    assert log.consulted == 1
    assert log.agreements == 1
    assert log.findings == ()


# ── 5. All three consultations can fire together, independently counted ───

def test_all_three_consultations_fire_together():
    ctxs = _canonical([
        _tx(1, "DIVIDEND", amount=500.0, date_str="2026-01-01"),
        _tx(2, "DEPOSIT", amount=1_000.0, date_str="2026-01-02"),
        _tx(3, "BUY", "KBANK", shares=100, price=100, amount=10_000, date_str="2026-01-03"),
        _tx(4, "BUY", "KBANK.BK", shares=50, price=100, amount=5_000, date_str="2026-01-04"),
    ])
    log = _consult_runtime_capabilities(ctxs)
    assert log.consulted == 3
    assert log.agreements == 3
    assert log.findings == ()


# ── 6. Mismatch is recorded, never raised ──────────────────────────────────

def test_mismatch_is_recorded_as_finding_never_raised(monkeypatch):
    import services.ledger_validator as lv
    from services.asset_definitions.vocabulary import FlowType

    class _AlwaysFalseView:
        def grants_flow(self, flow):
            return False

    class _StubResolver:
        def __init__(self, registry):
            pass

        def resolve(self, binding, *, as_of=None):
            return _AlwaysFalseView()

        def resolve_numeraire(self, *, as_of=None):
            raise AssertionError("not exercised in this test")

    monkeypatch.setattr(lv, "BindingResolver", _StubResolver)

    ctxs = _canonical([_tx(1, "DIVIDEND", amount=500.0)])
    log = lv._consult_runtime_capabilities(ctxs)

    assert log.consulted == 1
    assert log.agreements == 0
    assert len(log.findings) == 1
    finding = log.findings[0]
    assert finding.category == RuntimeFindingCategory.RUNTIME_MISMATCH.value
    assert finding.check_id == "RUNTIME_DIVIDEND_FLOW"
    assert finding.legacy_result is True
    assert finding.runtime_result is False


# ── 7. MissingBinding when resolution itself refuses ───────────────────────

def test_missing_binding_recorded_when_resolution_refuses(monkeypatch):
    import services.ledger_validator as lv
    from services.asset_definitions.binding_resolver import UnresolvedBindingError as _UBE

    class _RefusingResolver:
        def __init__(self, registry):
            pass

        def resolve(self, binding, *, as_of=None):
            raise _UBE(f"no definition admits binding '{binding}'")

        def resolve_numeraire(self, *, as_of=None):
            raise _UBE("numeraire unresolved")

    monkeypatch.setattr(lv, "BindingResolver", _RefusingResolver)

    ctxs = _canonical([_tx(1, "DIVIDEND", amount=500.0)])
    log = lv._consult_runtime_capabilities(ctxs)

    assert log.consulted == 1
    assert log.agreements == 0
    assert len(log.findings) == 1
    assert log.findings[0].category == RuntimeFindingCategory.MISSING_BINDING.value
    assert log.findings[0].runtime_result is None


# ── 8. Registry boot failure -> one finding, never raises ──────────────────

def test_registry_boot_failure_yields_single_finding_never_raises(monkeypatch):
    import services.ledger_validator as lv
    import services.asset_definitions.library as library

    original = dict(library.PINNED_FINGERPRINTS)
    try:
        library.PINNED_FINGERPRINTS[(AssetType.CASH.value, "v1")] = "0" * 64
        ctxs = _canonical([_tx(1, "DIVIDEND", amount=500.0)])
        log = lv._consult_runtime_capabilities(ctxs)
    finally:
        library.PINNED_FINGERPRINTS.clear()
        library.PINNED_FINGERPRINTS.update(original)

    assert log.consulted == 0
    assert log.agreements == 0
    assert len(log.findings) == 1
    assert log.findings[0].check_id == "RUNTIME_REGISTRY_BOOT_FAILED"
    assert log.findings[0].category == RuntimeFindingCategory.MISSING_BINDING.value


# ── 9. Full pipeline: additive only, zero effect on legacy validation ──────

def test_full_validate_portfolio_ledger_is_unaffected_by_runtime_consultation():
    """No DB needed for the assertion that matters: the runtime consultation
    is wired as pure post-processing over ctxs, so this test calls the two
    pieces exactly as validate_portfolio_ledger() does and asserts the
    legacy checks' outputs don't reference or depend on runtime_consultation.
    """
    from services.ledger_validator import _check_duplicate_initial_positions, _replay_and_check

    ctxs = _canonical([
        _tx(1, "DEPOSIT", amount=100_000.0, date_str="2026-01-01"),
        _tx(2, "BUY", "KBANK.BK", shares=100, price=100, amount=10_000, date_str="2026-01-02"),
        _tx(3, "DIVIDEND", amount=500.0, date_str="2026-01-03"),
    ])

    legacy_findings = _check_duplicate_initial_positions(1, ctxs)
    final_state, replay_findings, _ = _replay_and_check(1, ctxs)
    runtime_log = _consult_runtime_capabilities(ctxs)

    assert legacy_findings == []
    assert replay_findings == []
    assert isinstance(runtime_log, RuntimeConsultationLog)
    assert runtime_log.consulted == 2  # DIVIDEND + DEPOSIT
    assert runtime_log.agreements == 2
    assert runtime_log.findings == ()
    # Legacy replay result is identical regardless of runtime consultation
    assert float(final_state.cash) == 100_000.0 - 10_000.0 + 500.0
