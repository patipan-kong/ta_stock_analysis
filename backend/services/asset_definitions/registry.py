"""DefinitionRegistry — the loaded library (M9 TDD Section 2.1).

Built once at process start from the code-shipped transcriptions in
library.py, validated against the constitutional checks below, then frozen.
No reload, no hot-swap, no I/O on any query path (Section 1.3) — a new
definition or version arrives the way new code arrives: a deployment.

Boot validation (M9 TDD Section 6.1) is all-or-nothing: every violation
found is collected and reported together in one DefinitionRegistryError,
naming the definition, version, and violated rule — never a partial boot,
never a warning (this milestone's brief: "No warnings. Invalid definitions
must prevent boot.").

Deliberately absent: any check for "circular dependency," "invalid
inheritance," or "unresolved templates." The Asset Definition Library has no
inheritance or template mechanism — D6 (constitution) mandates a flat
capability plane with no hierarchy — so those defect classes have no
referent here. Building resolution machinery for them would introduce the
hierarchy D6 forbids, not guard against its absence. What replaces them:
the D1 duplicate-declaration check below is the actual "two things silently
collapsed into one" defect this library can have.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from services.asset_definitions import library
from services.asset_definitions.declarations import DefinitionTranscription
from services.asset_definitions.fingerprint import canonical_payload, compute_fingerprint
from services.asset_definitions.governance import GovernanceProjection
from services.asset_domain import AssetType


@dataclass(frozen=True)
class DefinitionValidationFinding:
    binding: str
    version: str
    rule: str
    message: str

    def __str__(self) -> str:
        return f"[{self.binding} {self.version}] {self.rule}: {self.message}"


class DefinitionRegistryError(Exception):
    """Raised at DefinitionRegistry.build() when the library fails boot
    validation. Carries every finding, not just the first — a malformed
    library is a build defect, and the platform should see the whole
    defect list in one failure, not one crash-fix-recrash cycle at a time.
    """

    def __init__(self, findings: List[DefinitionValidationFinding]) -> None:
        self.findings = findings
        joined = "; ".join(str(f) for f in findings)
        super().__init__(f"Asset Definition Library failed boot validation ({len(findings)} finding(s)): {joined}")


def _validate(
    ladders: Dict[str, Tuple[DefinitionTranscription, ...]],
    pinned_fingerprints: Dict[Tuple[str, str], str],
) -> List[DefinitionValidationFinding]:
    findings: List[DefinitionValidationFinding] = []
    valid_bindings = {member.value for member in AssetType}
    current_payloads: Dict[Tuple[object, ...], str] = {}

    for binding, ladder in ladders.items():
        if binding not in valid_bindings:
            findings.append(DefinitionValidationFinding(
                binding, "-", "unknown-binding",
                f"binding '{binding}' is not a member of AssetType; the library may only bind to spellings "
                "the platform already knows how to mint",
            ))
            continue

        if not ladder:
            findings.append(DefinitionValidationFinding(binding, "-", "empty-ladder", "ladder has no versions"))
            continue

        seen_versions: Dict[str, str] = {}
        previous_effective_from: Optional[str] = None
        for transcription in ladder:
            v = transcription.version

            if transcription.binding != binding:
                findings.append(DefinitionValidationFinding(
                    binding, v, "binding-mismatch",
                    f"transcription.binding={transcription.binding!r} does not match its ladder key {binding!r}",
                ))

            if v in seen_versions:
                findings.append(DefinitionValidationFinding(
                    binding, v, "duplicate-version", f"version '{v}' appears more than once in the ladder",
                ))
            seen_versions[v] = transcription.effective_from

            if previous_effective_from is not None and transcription.effective_from <= previous_effective_from:
                findings.append(DefinitionValidationFinding(
                    binding, v, "ladder-ordering",
                    f"effective_from {transcription.effective_from!r} does not strictly follow "
                    f"the prior rung's {previous_effective_from!r} (D8 — the ladder must be strictly ordered)",
                ))
            previous_effective_from = transcription.effective_from

            # D7 / referential integrity: a relationship kind cannot be
            # mandatory without also being permitted.
            unpermitted_mandatory = (
                transcription.existence.mandatory_relationships - transcription.existence.permitted_relationships
            )
            if unpermitted_mandatory:
                findings.append(DefinitionValidationFinding(
                    binding, v, "invalid-existence-reference",
                    f"mandatory_relationships contains kinds not in permitted_relationships: "
                    f"{sorted(k.value for k in unpermitted_mandatory)}",
                ))

            # Section 5.4: the transcription must not have moved since
            # publication.
            key = (binding, v)
            expected = pinned_fingerprints.get(key)
            if expected is None:
                findings.append(DefinitionValidationFinding(
                    binding, v, "missing-fingerprint-pin",
                    "no pinned fingerprint for this (binding, version) in library.PINNED_FINGERPRINTS",
                ))
            else:
                actual = compute_fingerprint(transcription)
                if actual != expected:
                    findings.append(DefinitionValidationFinding(
                        binding, v, "fingerprint-mismatch",
                        "computed fingerprint does not match the pinned manifest — this published version's "
                        "declarations moved after publication (constitution risk 10.8, retroactive redefinition)",
                    ))

            # D1: no two *current* (latest-per-ladder) definitions may share
            # an identical declaration payload. Only checked on the latest
            # rung of each ladder — a superseded version legitimately may
            # share history with what replaced it.
            if transcription is ladder[-1]:
                payload = canonical_payload(transcription)
                collision = current_payloads.get(payload)
                if collision is not None:
                    findings.append(DefinitionValidationFinding(
                        binding, v, "duplicate-declarations",
                        f"declares an identical capability payload to '{collision}' (D1 individuation violated)",
                    ))
                else:
                    current_payloads[payload] = binding

    return findings


class DefinitionRegistry:
    """The boot-built, frozen collection of every (definition, version)
    transcription. See module docstring."""

    def __init__(self, ladders: Dict[str, Tuple[DefinitionTranscription, ...]]) -> None:
        self._ladders = ladders

    @classmethod
    def build(cls) -> "DefinitionRegistry":
        findings = _validate(library.DEFINITION_LADDERS, library.PINNED_FINGERPRINTS)
        if findings:
            raise DefinitionRegistryError(findings)
        return cls(library.DEFINITION_LADDERS)

    def exists(self, binding: str) -> bool:
        return binding in self._ladders

    def _resolve_transcription(
        self, binding: str, *, as_of: Optional[str] = None
    ) -> Optional[DefinitionTranscription]:
        """Package-private: the latest rung whose effective_from <= as_of
        (or the latest rung overall when as_of is None). Used by
        BindingResolver and by get()/all() below — never exported as public
        API, because it hands back a raw transcription rather than either
        of the two governed doors (CapabilityView / GovernanceProjection).
        """
        ladder = self._ladders.get(binding)
        if not ladder:
            return None
        if as_of is None:
            return ladder[-1]
        governing = None
        for transcription in ladder:
            if transcription.effective_from <= as_of:
                governing = transcription
            else:
                break
        return governing

    def get(self, binding: str, *, as_of: Optional[str] = None) -> Optional[GovernanceProjection]:
        transcription = self._resolve_transcription(binding, as_of=as_of)
        if transcription is None:
            return None
        return GovernanceProjection(transcription)

    def all(self) -> Tuple[GovernanceProjection, ...]:
        return tuple(
            GovernanceProjection(ladder[-1])
            for binding, ladder in sorted(self._ladders.items())
        )
