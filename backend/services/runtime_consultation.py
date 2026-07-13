"""Shared shapes for Asset Definition Runtime shadow consultations
(Runtime Adoption Stage R1 — M11 brief, extended to further consumers by
the M12 brief).

Every R1 consumer follows the same pattern: ask the runtime the question
Legacy logic already answers implicitly, and record agreement/disagreement
as data — never raise, never change the caller's outcome. This module holds
the one shared vocabulary for that comparison so each consumer (ledger
validator, asset registry, ...) doesn't redefine its own copy of the same
three shapes.

Consumers remain responsible for deciding *which* legacy decisions are
genuinely shadowable — see each consumer module's own
`_consult_runtime_*()` docstring for that reasoning. This module defines
only the vocabulary the comparison is expressed in.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RuntimeFindingCategory(str, Enum):
    """Taxonomy for Stage R1 Legacy-vs-Runtime disagreements (M11 brief).

    Not every category is reachable by every consumer — a consumer only
    triggers the categories its own consultations can actually produce.
    They are all named here regardless, verbatim from the brief, so the
    taxonomy is complete and shared rather than redefined per consumer.
    """
    RUNTIME_MISMATCH   = "RuntimeMismatch"
    UNKNOWN_CAPABILITY = "UnknownCapability"
    MISSING_BINDING    = "MissingBinding"
    UNEXPECTED_GRANT   = "UnexpectedGrant"


@dataclass(frozen=True)
class RuntimeValidationFinding:
    """One Legacy-vs-Runtime disagreement, or a MissingBinding refusal.

    Purely observational (M11 brief: "Do NOT throw / reject / change
    behavior / change validation result"). Never merged into a consumer's
    own findings/result, never affects any existing outcome field.

    `transaction_ids` is empty for consumers with no transaction concept
    (e.g. the Asset Registry) — kept on the shared shape rather than
    renamed, since it is already part of the tested contract for the
    ledger validator's own findings.
    """
    category:        str
    check_id:        str
    transaction_ids: tuple[int, ...]
    binding:         str
    question:        str
    legacy_result:   bool
    runtime_result:  bool | None
    detail:          str


@dataclass(frozen=True)
class RuntimeConsultationLog:
    """Stage R1 shadow-comparison output for one consultation run.

    consulted   — number of Legacy-vs-Runtime questions asked.
    agreements  — number of those where legacy_result == runtime_result.
    findings    — every disagreement / refusal, as RuntimeValidationFinding.

    Additive metadata only. Its presence or contents never influence the
    consumer's own result, severity, or any other existing field.
    """
    consulted:  int
    agreements: int
    findings:   tuple[RuntimeValidationFinding, ...]
