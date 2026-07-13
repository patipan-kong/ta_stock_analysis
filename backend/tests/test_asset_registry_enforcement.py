"""Stage R2 (M14 brief): First Controlled Runtime Enforcement Gate.

Coverage
--------
  1.  Existing behavior preservation: enforcement_mode=OFF (and the
      unset-argument default) mints every AssetType exactly as before M14.
  2.  Shadow behavior: evaluate_mint_enforcement() computes the correct
      intended_action for every real M13 decision without ever setting
      blocked=True, even in SHADOW mode.
  3.  Enabled enforcement: only a synthetic REJECT decision blocks, and only
      that binding — every other binding in the same synthetic table still
      allows, proving the gate is narrow and decision-driven, not a blanket
      switch.
  4.  Rollback: the same asset_type/decision flips between blocked and
      allowed purely by changing `mode=`, with no memory between calls.
  5.  Decision consistency: real production ENFORCEMENT_DECISIONS has no
      REJECT row today, so ENFORCE mode against real data blocks nothing —
      mint() succeeds for all nine AssetType members even under ENFORCE.
  6.  Observability: mint() logs asset_type/mode/gap_type/action/reason on
      every call.
  7.  Configurability: an explicit `enforcement_mode=` argument to mint()
      overrides the ASSET_MINT_ENFORCEMENT_MODE environment variable.
"""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
from services import asset_registry as registry
from services.asset_definitions.enforcement_decisions import (
    ENFORCEMENT_DECISIONS,
    EnforcementDecision,
    FutureAction,
    GapType,
)
from services.asset_definitions.enforcement_gate import (
    ENFORCEMENT_MODE_ENV_VAR,
    EnforcementAction,
    EnforcementMode,
    evaluate_mint_enforcement,
)
from services.asset_domain import AssetClaim, AssetType

_ALL_TYPES = tuple(AssetType)


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _claim(**overrides):
    defaults = dict(
        canonical_symbol="KBANK",
        asset_type=AssetType.EQUITY,
        market="TH",
        exchange="SET",
        currency="THB",
    )
    defaults.update(overrides)
    return AssetClaim(**defaults)


def _synthetic_decisions_with_reject(rejected: AssetType) -> tuple:
    """A decisions table shaped like ENFORCEMENT_DECISIONS but with exactly
    one binding classified REJECT, to prove the blocking path exists
    without adding a REJECT row to the real, hand-authored M13 table
    (M14 non-goal: "do not enforce all missing definitions")."""
    out = []
    for d in ENFORCEMENT_DECISIONS:
        if d.binding == rejected.value:
            out.append(EnforcementDecision(
                binding=d.binding,
                consumer=d.consumer,
                gap_type=GapType.FUTURE_ENFORCEMENT_CANDIDATE,
                future_action=FutureAction.REJECT,
                rationale="synthetic test-only REJECT decision",
                r2_note="test fixture only — never present in the real table",
            ))
        else:
            out.append(d)
    return tuple(out)


# ── 1. Existing behavior preservation (mode OFF / unset) ───────────────────

@pytest.mark.parametrize("asset_type", _ALL_TYPES)
def test_mint_succeeds_for_every_asset_type_with_enforcement_off(asset_type):
    db = make_session()
    asset = registry.mint(
        db,
        _claim(canonical_symbol=f"OFF_{asset_type.value}", asset_type=asset_type),
        enforcement_mode=EnforcementMode.OFF,
    )
    assert asset.id is not None
    assert asset.asset_type == asset_type.value


@pytest.mark.parametrize("asset_type", _ALL_TYPES)
def test_mint_succeeds_for_every_asset_type_with_default_argument(asset_type, monkeypatch):
    monkeypatch.delenv(ENFORCEMENT_MODE_ENV_VAR, raising=False)
    db = make_session()
    asset = registry.mint(
        db, _claim(canonical_symbol=f"DEFAULT_{asset_type.value}", asset_type=asset_type),
    )
    assert asset.id is not None


# ── 2. Shadow behavior: correct intended_action, never blocked ─────────────

def test_shadow_mode_matches_decision_table_but_never_blocks():
    for asset_type in _ALL_TYPES:
        outcome = evaluate_mint_enforcement(asset_type, mode=EnforcementMode.SHADOW)
        assert outcome.blocked is False
        assert outcome.effective_action == EnforcementAction.ALLOW
        # Against real data every intended_action is ALLOW too (no REJECT exists yet).
        assert outcome.intended_action == EnforcementAction.ALLOW


def test_shadow_mode_computes_block_intent_without_applying_it():
    outcome = evaluate_mint_enforcement(
        AssetType.ETF, mode=EnforcementMode.SHADOW,
        decisions=_synthetic_decisions_with_reject(AssetType.ETF),
    )
    assert outcome.intended_action == EnforcementAction.BLOCK
    assert outcome.effective_action == EnforcementAction.ALLOW
    assert outcome.blocked is False


# ── 3. Enabled enforcement: narrow, only the approved case blocks ──────────

def test_enforce_mode_blocks_only_the_synthetic_reject_binding():
    decisions = _synthetic_decisions_with_reject(AssetType.ETF)

    blocked_outcome = evaluate_mint_enforcement(AssetType.ETF, mode=EnforcementMode.ENFORCE, decisions=decisions)
    assert blocked_outcome.blocked is True
    assert blocked_outcome.effective_action == EnforcementAction.BLOCK

    for asset_type in _ALL_TYPES:
        if asset_type == AssetType.ETF:
            continue
        outcome = evaluate_mint_enforcement(asset_type, mode=EnforcementMode.ENFORCE, decisions=decisions)
        assert outcome.blocked is False, f"{asset_type} must not be affected by ETF's synthetic REJECT"


def test_mint_raises_asset_registry_error_when_enforce_blocks(monkeypatch):
    decisions = _synthetic_decisions_with_reject(AssetType.ETF)
    monkeypatch.setattr(
        registry, "evaluate_mint_enforcement",
        lambda asset_type, *, mode=None: evaluate_mint_enforcement(asset_type, mode=mode, decisions=decisions),
    )

    db = make_session()
    with pytest.raises(registry.AssetRegistryError, match="blocked by Asset Definition Runtime"):
        registry.mint(
            db, _claim(canonical_symbol="BLOCKED_ETF", asset_type=AssetType.ETF),
            enforcement_mode=EnforcementMode.ENFORCE,
        )


def test_mint_not_blocked_for_other_types_when_enforce_blocks_etf(monkeypatch):
    decisions = _synthetic_decisions_with_reject(AssetType.ETF)
    monkeypatch.setattr(
        registry, "evaluate_mint_enforcement",
        lambda asset_type, *, mode=None: evaluate_mint_enforcement(asset_type, mode=mode, decisions=decisions),
    )

    db = make_session()
    asset = registry.mint(
        db, _claim(canonical_symbol="STILL_OK_FUND", asset_type=AssetType.FUND),
        enforcement_mode=EnforcementMode.ENFORCE,
    )
    assert asset.id is not None


# ── 4. Rollback: mode alone flips the outcome, no memory between calls ─────

def test_rollback_via_mode_alone_is_stateless():
    decisions = _synthetic_decisions_with_reject(AssetType.BOND)
    sequence = [EnforcementMode.OFF, EnforcementMode.SHADOW, EnforcementMode.ENFORCE, EnforcementMode.OFF]
    expected_blocked = [False, False, True, False]

    actual = [
        evaluate_mint_enforcement(AssetType.BOND, mode=mode, decisions=decisions).blocked
        for mode in sequence
    ]
    assert actual == expected_blocked


# ── 5. Decision consistency: real table authorizes zero rejections today ───

def test_no_real_decision_is_reject_today():
    assert all(d.future_action != FutureAction.REJECT for d in ENFORCEMENT_DECISIONS)


@pytest.mark.parametrize("asset_type", _ALL_TYPES)
def test_enforce_mode_against_real_decisions_blocks_nothing_today(asset_type):
    outcome = evaluate_mint_enforcement(asset_type, mode=EnforcementMode.ENFORCE)
    assert outcome.blocked is False


@pytest.mark.parametrize("asset_type", _ALL_TYPES)
def test_mint_succeeds_for_every_asset_type_with_enforce_mode_today(asset_type):
    db = make_session()
    asset = registry.mint(
        db, _claim(canonical_symbol=f"ENFORCE_{asset_type.value}", asset_type=asset_type),
        enforcement_mode=EnforcementMode.ENFORCE,
    )
    assert asset.id is not None


# ── 6. Observability ────────────────────────────────────────────────────────

def test_mint_logs_enforcement_outcome(caplog):
    db = make_session()
    with caplog.at_level(logging.INFO, logger="services.asset_registry"):
        registry.mint(db, _claim(canonical_symbol="LOGGED", asset_type=AssetType.FUND))

    matching = [r for r in caplog.records if "asset_definition_enforcement" in r.message]
    assert len(matching) == 1
    message = matching[0].message
    assert "asset_type=FUND" in message
    assert "mode=OFF" in message
    assert "effective_action=Allow" in message
    assert "reason=" in message


# ── 7. Configurability: explicit argument overrides the env var ────────────

def test_explicit_mode_argument_overrides_env_var(monkeypatch):
    monkeypatch.setenv(ENFORCEMENT_MODE_ENV_VAR, "ENFORCE")
    outcome = evaluate_mint_enforcement(AssetType.CASH, mode=EnforcementMode.OFF)
    assert outcome.mode == EnforcementMode.OFF


def test_env_var_used_when_argument_omitted(monkeypatch):
    monkeypatch.setenv(ENFORCEMENT_MODE_ENV_VAR, "SHADOW")
    outcome = evaluate_mint_enforcement(AssetType.CASH)
    assert outcome.mode == EnforcementMode.SHADOW


def test_unrecognized_env_var_value_defaults_to_off(monkeypatch):
    monkeypatch.setenv(ENFORCEMENT_MODE_ENV_VAR, "NOT_A_MODE")
    outcome = evaluate_mint_enforcement(AssetType.CASH)
    assert outcome.mode == EnforcementMode.OFF


# ── Unrecorded binding defensiveness ────────────────────────────────────────

def test_missing_decision_for_binding_allows_by_default():
    outcome = evaluate_mint_enforcement(AssetType.CASH, mode=EnforcementMode.ENFORCE, decisions=())
    assert outcome.blocked is False
    assert outcome.gap_type == "Unrecorded"
