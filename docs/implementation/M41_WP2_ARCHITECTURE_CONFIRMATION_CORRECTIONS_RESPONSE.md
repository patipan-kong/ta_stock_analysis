# M41-WP2 — Architecture Confirmation Corrections Response

**Response role:** Implementation Author

**Artifacts and authority:**

- [M41-WP2 Architecture Proposal](M41_WP2_ARCHITECTURE_PROPOSAL.md) — updated by this response
- [M41-WP2 Independent Architecture Review](M41_WP2_ARCHITECTURE_INDEPENDENT_REVIEW.md) — frozen, cited
- [M41-WP2 Required Corrections Response](M41_WP2_REQUIRED_CORRECTIONS_RESPONSE.md) — frozen, cited
- [M41-WP2 Architecture Confirmation](M41_WP2_ARCHITECTURE_CONFIRMATION.md) (`NOT CONFIRMED`) — frozen, cited, sole authority for this correction round

**Architecture authority:** Frozen (cited, not modified)

**M41-WP1 authority:** Frozen (cited, not modified)

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API authority:** `NONE`

**Response date:** 2026-07-23

---

## Scope

This response resolves only the two unresolved correction items recorded by
the first M41-WP2 Architecture Confirmation (`NOT CONFIRMED`):
M41-WP2-AC-1 and M41-WP2-AC-2. It does not reopen M41-WP2-AR-1,
M41-WP2-AR-2, M41-WP2-AR-3, M41-WP2-AR-6, M41-WP2-AR-7, or the already-
resolved portions of M41-WP2-AR-4 and M41-WP2-AR-5. It does not modify the
Independent Architecture Review or the first Architecture Confirmation, does
not introduce a new finding, does not begin WP2-Stage A or WP2-Stage B, and
does not claim Architecture Confirmation. Only
`docs/implementation/M41_WP2_ARCHITECTURE_PROPOSAL.md` was modified; this
response document was newly created.

---

## M41-WP2-AC-1 Resolution

**Finding:** The Stage A deliverable definition (§11) predetermined
`Market Intelligence` as the owner of every Stage A vocabulary candidate,
contradicting §4's statement that no candidate is pre-owned.

**Correction applied:** §11's Stage A deliverable bullet no longer names a
specific owner. It now reads that each candidate entry requires "a
determined single owner, justified through the governed candidate-admission
workflow and recorded as a Stage A ownership disposition — this architecture
proposal pre-owns and pre-admits no candidate, and does not name a specific
owner in advance," and closes with "Every confirmed governed noun ends
Stage A with exactly one determined owner."

This removes the predetermined owner while preserving the requirement that
Stage A must still determine and record exactly one owner per candidate
before that candidate can be relied upon — the governance discipline itself
is unchanged, only the premature naming of the owner is removed.

**Review for other pre-ownership wording:** The full proposal was searched
for `Market Intelligence` and for other ownership language. No other
occurrence of `Market Intelligence` remains anywhere in the document. The
three Stage A candidates — Subject Reference, Subject Ordering Key, Manifest
Entry — are listed in §4 without any assigned owner, each marked "candidate
under evaluation" with no disposition or owner stated. No other section
assigns an owner to any candidate. The confirmed ordinary-language
classifications (manifest identity, equivalence/conflict disposition,
canonical serialization) were not touched.

**Sections changed:** §11 (Stage A deliverable bullet) only.

---

## M41-WP2-AC-2 Resolution

**Finding:** The expanded validation matrix included a Measure Subject
shape-(b) ordering-permutation pair but omitted the separately required
Observation Input Manifest entry-ordering-permutation case.

**Correction applied:** An explicit Observation Input Manifest
entry-ordering-permutation case was added, distinct from the Subject
ordering-permutation pair, at every location that previously listed the
Subject case alone:

- **§2, Included scope (golden vectors bullet):** now lists, alongside the
  Subject ordering-permutation pair, "one Observation Input Manifest
  entry-ordering-permutation case (distinct from the Subject
  ordering-permutation pair — differently ordered representations of the
  same valid manifest entry set resolving through the normative ordering
  rule to the same canonical Manifest serialization and identity)."
- **§8, Validation strategy (golden vectors bullet):** now lists "a
  shape-(b) Subject ordering-permutation pair, an Observation Input Manifest
  entry-ordering-permutation case distinct from the Subject
  ordering-permutation pair."
- **§11, Stage B deliverable bullet:** the validation-matrix reference now
  reads "the complete golden-vector/ordering-permutation/round-trip/
  provider-leak-rejection/exact-evidence-reproduction validation matrix
  listed in §8 above, covering both Subject ordering permutations and the
  distinct Observation Input Manifest entry-ordering-permutation case."

The added case demonstrates that differently ordered representations of the
same valid Manifest entry set resolve, through the manifest's own normative
ordering rule, to one canonical Manifest serialization and one Manifest
identity — mirroring the Subject case's structure without merging the two.
Manifest membership remains limited strictly to exact frozen M39 Observation
evidence; no other input category was added to manifest scope. Measure
Subject ordering semantics (§5, Component 3) were not modified.

**Sections changed:** §2, §8, §11 (each an addition alongside existing text,
not a replacement of the Subject case).

---

## Preservation of Previously Resolved Findings

The following remain resolved and were not reopened or materially changed by
this response:

| Finding | Preserved as |
|---|---|
| M41-WP2-AR-1 | Exact WP1 field ownership (Market Measure Definition §5.4 permitted-input declaration; Method Requirement §7.4/§7.4a prerequisite category and evaluation rule) — untouched in §§0, 1, 2, 5, 6, 9. |
| M41-WP2-AR-2 | Observation Input Manifest membership limited to exact M39 Observation evidence — untouched in §§0, 2, 5, 6; the new AC-2 ordering-permutation case is itself scoped to that same exact-M39-evidence membership. |
| M41-WP2-AR-3 | Definition Version excluded from all three Measure Subject shapes, retained only as its own separately owned binding coordinate — untouched in §§2, 5, 6, 9. |
| M41-WP2-AR-4 (resolved portion) | Manifest identity, equivalence/conflict disposition, and canonical serialization remain classified as ordinary non-canonical contract language (register §6.0) in §4 and §11 — untouched. |
| M41-WP2-AR-5 (resolved portion) | Measure Subject canonical serialization remains explicit in §1, §2, §5 (Component 4), §8, and §11 — untouched; only extended by the new distinct Manifest ordering-permutation case, not altered. |
| M41-WP2-AR-6 | Conflict handling remains closed to existing frozen `Computation Outcome` values, with Result composition and degraded-state interaction left to WP4 — untouched in §§1, 2, 5, 6, 9. |
| M41-WP2-AR-7 | Formal proposal header, full authority fields, complete Stage A governance workflow (definition, ownership disposition, overlap, V1–V3, M34/M39/M40 compatibility, five-part gate, unconditional Independent Confirmation), and distinct Stage A/Stage B review artifact filenames — untouched in the document header and §11, apart from the AC-1 ownership-wording correction itself. |

No wording changed outside the three sections (§2, §8, §11) touched for
AC-1/AC-2, and no change in those sections altered any other finding's
resolution.

---

## Repository Validation

- Only two files were involved in this response: `M41_WP2_ARCHITECTURE_PROPOSAL.md`
  (modified) and this document (created). No other repository file was
  modified or created.
- `M41_ARCHITECTURE_PROPOSAL.md`, all M41-WP1 artifacts, `GLOSSARY.md`,
  `docs/engineering/DECISION_LOG.md`, and `docs/implementation/INDEX.md`
  were not modified.
- `M41_WP2_ARCHITECTURE_INDEPENDENT_REVIEW.md` and
  `M41_WP2_ARCHITECTURE_CONFIRMATION.md` were not modified.
- Graphify was not refreshed.
- No `M41_WP2_STAGE_A_*` or `M41_WP2_STAGE_B_*` artifact exists. WP2-Stage A
  and WP2-Stage B have not begun.
- No implementation, runtime, provider, persistence, or API behavior was
  introduced; all five operational authority fields remain `NONE`.
- No new finding was introduced; only the two named corrections were
  applied.
- Markdown structure (code-fence balance, heading sequence) and
  `git diff --check` were validated clean for both files.

---

## Final Status

M41-WP2-AC-1 and M41-WP2-AC-2 are both resolved. This response does not
constitute Architecture Confirmation; a further confirmation pass by the
Independent Architecture Review Board is required to close this correction
round.
