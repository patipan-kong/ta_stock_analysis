"""Runtime Enforcement Gate — Stage R2, first controlled gate (M14 brief).

Stage R1/R1.5 (M11-M13) only ever *observed*: every consultation logged
agreement/disagreement and never changed a caller's outcome. This module is
the first place a runtime-driven decision is allowed to change what happens
— and only for one consumer (asset_registry.mint()), only for one already
-documented decision table (enforcement_decisions.ENFORCEMENT_DECISIONS,
M13), and only when explicitly switched on.

Enforcement follows decisions, it does not infer them (M14 brief,
"Enforcement must follow decisions"). The only thing this module reads to
decide ALLOW vs BLOCK is EnforcementDecision.future_action:

  NOT_APPLICABLE  (no gap)              -> ALLOW
  PRESERVE        (intentional legacy)  -> ALLOW, preserves current behavior
  MIGRATE         (missing definition,
                    migration required) -> ALLOW — a MIGRATE verdict is
                    explicitly *not* an authorization to reject (M14 brief:
                    "Do not silently reject unless the M13 decision
                    explicitly authorizes it")
  REJECT                                -> BLOCK

As of this milestone no entry in ENFORCEMENT_DECISIONS has future_action
REJECT (see that module) — so turning enforcement_mode to ENFORCE against
the real production table is a documented no-op today. The blocking path
itself is proven by the unit tests in test_asset_registry_enforcement.py,
which inject a synthetic decisions tuple containing a REJECT row rather
than adding one to the real table (M14 non-goals: "do not enforce all
missing definitions", "do not reject all undefined AssetTypes", "do not add
new Asset Definitions").

Rollout safety (M14 brief, "Rollout Safety"): three modes, OFF/SHADOW/
ENFORCE. Only ENFORCE can ever set `blocked=True` on the returned outcome
— OFF and SHADOW always resolve to effective_action=ALLOW, so `blocked` is
always False for them regardless of what the decision table says. Mode is
resolved per call (an explicit `mode=` argument, or else the
ASSET_MINT_ENFORCEMENT_MODE environment variable, or else OFF) — there is
no persisted/global mutable state, so changing mode between calls has no
memory: rollback is simply calling again with a different mode.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from services.asset_definitions.enforcement_decisions import (
    ENFORCEMENT_DECISIONS,
    EnforcementDecision,
    FutureAction,
)
from services.asset_domain import AssetType

_log = logging.getLogger(__name__)

ENFORCEMENT_MODE_ENV_VAR = "ASSET_MINT_ENFORCEMENT_MODE"


class EnforcementMode(str, Enum):
    """OFF is the default and is the only mode guaranteed byte-identical to
    pre-M14 behavior — new deployments and existing callers that never pass
    `enforcement_mode` get OFF automatically."""

    OFF     = "OFF"
    SHADOW  = "SHADOW"
    ENFORCE = "ENFORCE"


class EnforcementAction(str, Enum):
    ALLOW = "Allow"
    BLOCK = "Block"


@dataclass(frozen=True)
class EnforcementOutcome:
    """One enforcement evaluation, fully observable (M14 brief, "Required
    Observability": asset type, runtime decision, enforcement mode, action
    taken, reason are all present as fields, not just log text).

    intended_action  — what EnforcementDecision.future_action alone implies,
                        independent of mode.
    effective_action — what actually happens this call. Equals
                        intended_action only when mode == ENFORCE; otherwise
                        always ALLOW.
    blocked          — effective_action == BLOCK. The only field the caller
                        needs to check to decide whether to raise.
    """
    asset_type:       str
    mode:             EnforcementMode
    gap_type:         str
    intended_action:  EnforcementAction
    effective_action: EnforcementAction
    blocked:          bool
    reason:           str


def _mode_from_env() -> EnforcementMode:
    raw = os.environ.get(ENFORCEMENT_MODE_ENV_VAR, EnforcementMode.OFF.value).strip().upper()
    try:
        return EnforcementMode(raw)
    except ValueError:
        _log.warning(
            "%s=%r is not a recognized enforcement mode (OFF/SHADOW/ENFORCE) — defaulting to OFF",
            ENFORCEMENT_MODE_ENV_VAR, raw,
        )
        return EnforcementMode.OFF


def _find_decision(
    binding: str, decisions: Tuple[EnforcementDecision, ...],
) -> Optional[EnforcementDecision]:
    for decision in decisions:
        if decision.binding == binding:
            return decision
    return None


def evaluate_mint_enforcement(
    asset_type: AssetType,
    *,
    mode: Optional[EnforcementMode] = None,
    decisions: Tuple[EnforcementDecision, ...] = ENFORCEMENT_DECISIONS,
) -> EnforcementOutcome:
    """Never raises. Callers decide what to do with `outcome.blocked` —
    this function only evaluates, it does not enforce by itself.

    `decisions` defaults to the real, hand-authored M13 table but accepts an
    override so tests can prove the ENFORCE blocking path exists without
    fabricating a REJECT entry in production data.
    """
    resolved_mode = mode if mode is not None else _mode_from_env()
    decision = _find_decision(asset_type.value, decisions)

    if decision is None:
        return EnforcementOutcome(
            asset_type=asset_type.value,
            mode=resolved_mode,
            gap_type="Unrecorded",
            intended_action=EnforcementAction.ALLOW,
            effective_action=EnforcementAction.ALLOW,
            blocked=False,
            reason=(
                f"no enforcement decision recorded for binding {asset_type.value!r}; "
                "defaulting to allow"
            ),
        )

    intended_action = (
        EnforcementAction.BLOCK if decision.future_action == FutureAction.REJECT
        else EnforcementAction.ALLOW
    )
    effective_action = (
        intended_action if resolved_mode == EnforcementMode.ENFORCE
        else EnforcementAction.ALLOW
    )

    return EnforcementOutcome(
        asset_type=asset_type.value,
        mode=resolved_mode,
        gap_type=decision.gap_type.value,
        intended_action=intended_action,
        effective_action=effective_action,
        blocked=effective_action == EnforcementAction.BLOCK,
        reason=decision.rationale,
    )
