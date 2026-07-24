# M41-WP2 Stage A — Required Corrections Response

**Response role:** Implementation Author

**Reviewed artifact:** [M41-WP2 Stage A Independent Review](M41_WP2_STAGE_A_INDEPENDENT_REVIEW.md) (`APPROVED WITH REQUIRED CORRECTIONS`, 2026-07-23)

**Corrected artifact:** [M41-WP2 Stage A Candidate Vocabulary Register](M41_WP2_STAGE_A_CANDIDATE_VOCABULARY_REGISTER.md)

**Architecture authority:** Frozen (cited, not modified)

**M41-WP1 authority:** Frozen (cited, not modified)

**M41-WP2 Architecture authority:** Frozen (cited, not modified)

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API authority:** `NONE`

**Response date:** 2026-07-23

---

## Scope

This response resolves only the single finding recorded by the M41-WP2 Stage
A Independent Review (`APPROVED WITH REQUIRED CORRECTIONS`): **M41-WP2-SA-IR-1**.
The Independent Review is treated as authoritative. This response does not
redesign Stage A, does not revisit any candidate disposition, does not begin
WP2-Stage B, and does not perform Independent Confirmation. Only
`docs/implementation/M41_WP2_STAGE_A_CANDIDATE_VOCABULARY_REGISTER.md` was
modified; this response document was newly created. No other repository file
was modified.

---

## M41-WP2-SA-IR-1 Resolution

**Finding:** Subject Reference and Subject Ordering Key each recorded their
proposed owner as absent (`Not proposed by this document`) with an `N/A`
ownership rationale. The confirmed WP2 Architecture §11 requires every Stage
A candidate entry to record a determined single owner through the governed
candidate-admission workflow; a `MERGE` disposition produces no new
ownership, but it must still identify the sole existing owner the candidate's
meaning merges into.

**Resolution:** Fixed.

- **Subject Reference (§3.1):** The `Proposed owner` field now reads
  "Asset Foundation — the existing canonical owner into which this
  candidate's meaning merges. No new ownership is created and no ownership
  transfer occurs." The `Ownership rationale` field now states that Asset
  Foundation already and exclusively owns `asset_id`
  (`GLOSSARY.md#asset`, `GLOSSARY.md#asset-registry`), the exact reference
  Measure Subject cites, and records the explicit Stage A ownership
  disposition: "MERGE into Asset Foundation's existing `asset_id`." The
  `Disposition rationale` sentence naming the merged-into vocabulary was
  updated to state it is "owned by Asset Foundation."
- **Subject Ordering Key (§3.2):** The `Proposed owner` field now reads
  "Market Intelligence — the existing canonical owner into which this
  candidate's meaning merges. No new ownership is created and no ownership
  transfer occurs." The `Ownership rationale` field now states that Market
  Intelligence already owns the confirmed Measure Subject term in full,
  including its shape-(b) ordering obligation, and records the explicit
  Stage A ownership disposition: "MERGE into the confirmed Measure Subject
  ordering obligation, owned by Market Intelligence."
- **Disposition summary (§5):** The table column header was changed from
  "Proposed owner" to "Determined owner," and both `MERGE` rows now state
  the determined existing owner and "(no transfer)" explicitly, alongside
  Manifest Entry's "(new admission)" for contrast. The paragraph beneath the
  table was updated to state that every candidate records exactly one
  determined owner, and that for the two `MERGE` candidates the determined
  owner is the existing canonical owner of the concept each merges into,
  with no ownership transfer.
- **Validation (§6):** The "Exactly one proposed owner per candidate" bullet
  was renamed "Exactly one determined owner per candidate" and rewritten to
  state that Subject Reference records Asset Foundation and Subject Ordering
  Key records Market Intelligence as their determined existing owner, rather
  than stating no owner is proposed. The adjacent "No ownership conflicts"
  bullet was extended to state explicitly that no ownership transfer is
  implied or recorded.

No other field of either `MERGE` entry was changed. No candidate definition,
disposition, overlap analysis, compatibility analysis, or five-part
ownership-boundary gate was modified.

---

## Preservation of Candidate Dispositions

The following remain exactly as the Stage A register and its Independent
Review recorded them, and were not touched by this response:

| Candidate | Disposition | Preserved as |
|---|---|---|
| Subject Reference | `MERGE` | Definition, canonical/glossary/M39-M40 overlap analyses, negative corpus analysis, V1/V2/V3 analysis, M34/M39/M40 compatibility analysis, and five-part gate — unchanged; only the ownership field and its immediately adjacent disposition-rationale clause were corrected |
| Subject Ordering Key | `MERGE` | Definition, canonical/glossary/M39-M40 overlap analyses, negative corpus analysis, V1/V2/V3 analysis, M34/M39/M40 compatibility analysis, and five-part gate — unchanged; only the ownership field was corrected |
| Manifest Entry | `ADMIT` | Entirely untouched — proposed definition, owner (Market Intelligence), ownership rationale, all overlap analyses, negative corpus analysis, V1/V2/V3 analysis, M34/M39/M40 compatibility analysis, five-part gate, constitutional constraints, and glossary synchronization requirement are unchanged |
| Manifest Identity / Canonical Serialization / Evidence Equivalence / Evidence Conflict Determination | Frozen ordinary non-canonical contract language | Untouched — not evaluated as candidates before or after this correction |
| §4 Further-candidate determination | No additional governed noun required | Untouched |

No new governed noun is admitted by this response. No ownership transfer
occurs: Asset Foundation's ownership of `asset_id` and Market Intelligence's
ownership of the confirmed Measure Subject term are unchanged before and
after this correction — only the register's recording of those existing
ownership facts was corrected. Manifest Entry's `ADMIT` disposition and its
Market Intelligence ownership are unchanged; this response does not affect
Manifest Entry.

---

## Repository Validation

- Only two files were involved in this response:
  `docs/implementation/M41_WP2_STAGE_A_CANDIDATE_VOCABULARY_REGISTER.md`
  (modified) and this document (created). No other repository file was
  modified or created.
- `M41_WP2_STAGE_A_INDEPENDENT_REVIEW.md`, the M41 Architecture, all M41-WP1
  artifacts, the M41-WP2 Architecture Proposal and its confirmation chain,
  `GLOSSARY.md`, `docs/engineering/DECISION_LOG.md`, and
  `docs/implementation/INDEX.md` were not modified.
- Graphify was not refreshed.
- No `M41_WP2_STAGE_A_INDEPENDENT_CONFIRMATION.md` or any `M41_WP2_STAGE_B_*`
  artifact exists. Stage A Independent Confirmation has not been performed by
  this response, and WP2-Stage B has not begun.
- Every candidate in the corrected register now records exactly one
  determined owner: Asset Foundation (Subject Reference, `MERGE`, no
  transfer), Market Intelligence (Subject Ordering Key, `MERGE`, no
  transfer), Market Intelligence (Manifest Entry, `ADMIT`, new admission).
- No ownership transfer is implied or recorded for either `MERGE` candidate.
- No new governed noun is admitted by this response; the register continues
  to admit exactly one candidate, Manifest Entry, unchanged from the prior
  revision.
- No implementation, runtime, provider, persistence, or API behavior was
  introduced; all five operational authority fields remain `NONE`.
- Markdown structure (heading sequence, table formatting, code-fence
  balance — none used) was checked by inspection; no unclosed fence or
  malformed table is present in either file. `git diff --check` was
  validated clean for the modified register.

---

## Final Status

M41-WP2-SA-IR-1 is resolved. This response does not constitute Stage A
Independent Confirmation; a further confirmation pass by the Independent
Architecture Review Board is required to close Stage A.
