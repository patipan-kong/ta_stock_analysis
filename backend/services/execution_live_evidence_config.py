"""Central, legacy-safe switch for the optional M32.3E2 plan shadow."""
from __future__ import annotations

import os

__all__ = ["live_evidence_shadow_enabled"]


def live_evidence_shadow_enabled() -> bool:
    """Return true only for the one explicit opt-in value.

    Invalid, absent, and malformed values all safely disable the private
    diagnostic.  Pure evidence/policy helpers never import this module.
    """

    return os.environ.get("M32_LIVE_EVIDENCE_SHADOW", "OFF").strip().upper() == "ON"
