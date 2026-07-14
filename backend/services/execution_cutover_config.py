"""Central M31 execution-eligibility cutover configuration.

M31.5 introduces the vocabulary only.  No mode in this module changes
optimizer, plan, or transaction behaviour; later milestones must explicitly
wire any behaviour behind the typed value.
"""
from __future__ import annotations

import logging
import os
import threading
from enum import Enum
from typing import Mapping, Optional

__all__ = [
    "EXECUTION_ELIGIBILITY_CUTOVER_MODE_ENV",
    "ExecutionEligibilityCutoverMode",
    "ExecutionCutoverConfigurationError",
    "load_execution_eligibility_cutover_mode",
    "get_execution_eligibility_cutover_mode",
    "reset_execution_eligibility_cutover_mode_cache",
]


EXECUTION_ELIGIBILITY_CUTOVER_MODE_ENV = "EXECUTION_ELIGIBILITY_CUTOVER_MODE"


class ExecutionEligibilityCutoverMode(str, Enum):
    LEGACY_FALLBACK = "LEGACY_FALLBACK"
    FACTS_ONLY_SHADOW = "FACTS_ONLY_SHADOW"
    ENFORCE = "ENFORCE"


class ExecutionCutoverConfigurationError(ValueError):
    """Raised by strict loading when the configured mode is invalid."""


_log = logging.getLogger(__name__)
_lock = threading.Lock()
_cached_mode: Optional[ExecutionEligibilityCutoverMode] = None


def load_execution_eligibility_cutover_mode(
    environ: Optional[Mapping[str, str]] = None,
) -> ExecutionEligibilityCutoverMode:
    """Strictly parse the configured mode without caching it.

    A missing/blank value is deliberately the compatibility-preserving
    default.  An invalid non-blank value raises instead of silently selecting
    a more permissive or enforcing mode.
    """

    source = os.environ if environ is None else environ
    raw = source.get(EXECUTION_ELIGIBILITY_CUTOVER_MODE_ENV, "").strip().upper()
    if not raw:
        return ExecutionEligibilityCutoverMode.LEGACY_FALLBACK
    try:
        return ExecutionEligibilityCutoverMode(raw)
    except ValueError as exc:
        allowed = ", ".join(mode.value for mode in ExecutionEligibilityCutoverMode)
        raise ExecutionCutoverConfigurationError(
            f"invalid {EXECUTION_ELIGIBILITY_CUTOVER_MODE_ENV}={raw!r}; "
            f"allowed values: {allowed}"
        ) from exc


def get_execution_eligibility_cutover_mode() -> ExecutionEligibilityCutoverMode:
    """Return the process-wide mode, failing safely to LEGACY_FALLBACK.

    The strict loader remains available to startup/preflight code that wants
    to fail deployment configuration validation.  Runtime shadow telemetry
    must never break a legacy execution path, so its cached accessor logs an
    invalid value and selects the non-enforcing compatibility mode.
    """

    global _cached_mode
    with _lock:
        if _cached_mode is not None:
            return _cached_mode
        try:
            _cached_mode = load_execution_eligibility_cutover_mode()
        except ExecutionCutoverConfigurationError:
            _log.exception(
                "invalid execution eligibility cutover configuration; "
                "using LEGACY_FALLBACK and leaving enforcement disabled"
            )
            _cached_mode = ExecutionEligibilityCutoverMode.LEGACY_FALLBACK
        return _cached_mode


def reset_execution_eligibility_cutover_mode_cache() -> None:
    """Clear the process cache for tests and controlled configuration reloads."""

    global _cached_mode
    with _lock:
        _cached_mode = None
