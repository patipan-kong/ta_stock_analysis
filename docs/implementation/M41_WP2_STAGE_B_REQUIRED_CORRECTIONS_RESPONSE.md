# M41-WP2 Stage B — Required Corrections Response

**Response role:** Original Stage B Specification Author

**Authoritative review:** [M41-WP2 Stage B Independent Review](M41_WP2_STAGE_B_INDEPENDENT_REVIEW.md) (`APPROVED WITH REQUIRED CORRECTIONS`)

**Corrected artifact:** [M41-WP2 Stage B Subject and Manifest Contract Specification](M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md)

**Architecture authority:** Frozen (cited, not modified)

**M41-WP1 authority:** Frozen (cited, not modified)

**M41-WP2 Architecture authority:** Frozen (cited, not modified)

**M41-WP2 Stage A authority:** Frozen (cited, not modified)

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API authority:** `NONE`

**Response date:** 2026-07-24

---

## Executive Summary

This response implements only the correction required by
`M41-WP2-SB-IR-1`. The Stage B specification still requires
`ObservationEvidenceCount` to count distinct referenced M39 Observation
identities. Its justification now explicitly derives that result from the
frozen M41-WP1 wording, and one additional normative validation vector makes
the one-identity/two-requirement case mechanically unambiguous.

No semantic decision, contract structure, governed vocabulary, ownership,
serialization, canonical ordering, compatibility rule, architecture, or
authority was changed.

---

## Implemented Corrections

### 1. Explicit `ObservationEvidenceCount` derivation

Section 5.4(7) no longer merely asserts that distinct-identity counting
“exactly preserves” the frozen M41-WP1 meaning. It now states the required
derivation:

1. Manifest Entry did not exist when M41-WP1 froze.
2. M41-WP1 therefore could not have used “M39 Observation evidence records”
   to mean Manifest Entries.
3. The frozen phrase necessarily refers to the underlying admitted M39
   Observation evidence itself, identified by its M39 Observation identity.
4. Repeating one Observation identity across multiple requirement roles
   creates multiple Manifest Entries but does not create additional M39
   Observation evidence records.
5. `ObservationEvidenceCount` therefore equals the count of distinct
   referenced M39 Observation identities in the entire manifest.

The dependent validation clause in §7.2 and the M41-WP1 compatibility
statement in §8.4 now point to or restate this derivation without making the
unsupported preservation assertion. The semantic rule itself is unchanged.

### 2. Additional normative validation vector

Section 7.4.9 now supplies the required worked case:

- one admitted M39 Observation identity, `obs-001`;
- two distinct applicable requirement keys, `obs-role-a` and `obs-role-b`;
- two Manifest Entries, one for each requirement key and both referencing
  `obs-001`; and
- `ObservationEvidenceCount = 1`.

The vector displays both entries, the singleton set of distinct referenced
M39 Observation identities, and the resulting exact operand value. The
§7.5 validation matrix now cites this vector.

No other correction or improvement was made.

---

## Repository Validation

- Only
  `docs/implementation/M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md`
  and this response document were modified or created for this correction.
- M41 Architecture artifacts are unchanged.
- M41-WP1 artifacts are unchanged.
- M41-WP2 Architecture artifacts are unchanged.
- M41-WP2 Stage A artifacts and dispositions are unchanged.
- `docs/engineering/DECISION_LOG.md` is unchanged.
- `docs/GLOSSARY.md` is unchanged.
- `graphify-out/` is unchanged; Graphify was queried but not refreshed.
- `docs/implementation/INDEX.md` is unchanged.
- Observation Input Manifest and Manifest Entry were not redesigned.
- `ObservationEvidenceCount` semantics were not redesigned.
- Ownership, serialization, canonical ordering, compatibility, and
  architecture were not modified.
- No new governed vocabulary was introduced.
- No Stage C or WP3 work was performed.
- Implementation, runtime, provider, persistence, and API authority remain
  `NONE`.
- Markdown structure and code-fence balance were checked.
- Repository whitespace validation was completed with a clean
  `git diff --check`.

---

## Final Status

**READY FOR INDEPENDENT CONFIRMATION**
