# M34 Audit Working Artifacts

**Date:** 2026-07-17

**Status:** Active. M34-WP2 through M34-WP5 have populated the Corpus Register,
Evidence Register, Review Log, and work-package reports. WP5 returned its
authority handoff to the Architecture Review Board. The Finding and Decision
Registers remain empty.

**Authority:**
`docs/implementation/M34_WP1_charter_and_audit_protocol.md` is the governing
protocol. These working artifacts implement that protocol and must not amend
it. A conflict is resolved in favor of WP1 and returned to the Architecture
Review Board when material.

## 1. Purpose

This directory provides the controlled working records used throughout M34:

| Artifact | Canonical file | Purpose |
| --- | --- | --- |
| Evidence Register | `registers/evidence_register.md` | Records bounded observations and their provenance |
| Finding Register | `registers/finding_register.md` | Records verified audit concerns and readiness effects |
| Corpus Register | `registers/corpus_register.md` | Records declared areas and discovered in-scope or out-of-scope artifacts |
| Review Log | `registers/review_log.md` | Append-only record of verification, challenge, review, approval, and closure actions |
| Decision Register | `registers/decision_register.md` | Records approved dispositions, escalations, corpus amendments, and milestone decisions |

Each identifier has exactly one canonical record in exactly one register.
Links elsewhere are references, not copies or alternate sources of truth.

## 2. Identifier conventions

Identifiers are permanent, uppercase, repository-wide within M34, and use
four zero-padded decimal digits.

| Record | Format | Example placeholder |
| --- | --- | --- |
| Corpus item | `M34-C-####` | `M34-C-NNNN` |
| Evidence item | `M34-E-####` | `M34-E-NNNN` |
| Finding | `M34-F-####` | `M34-F-NNNN` |
| Review event | `M34-R-####` | `M34-R-NNNN` |
| Decision | `M34-D-####` | `M34-D-NNNN` |
| Work package | `M34-WP#` | `M34-WP1` |
| Review checkpoint | `M34-CP#` | `M34-CP0` |

Rules:

1. Allocate the next unused number from the canonical register; never infer it
   from row count, Git history, another branch, or a deleted draft.
2. Never reuse, renumber, overload, or silently delete an allocated id.
3. Gaps are permitted and remain unexplained unless allocation itself is
   disputed.
4. An id identifies one semantic record for its entire lifetime. Moving a
   record between files or changing its meaning is prohibited.
5. Corrections to verified evidence and approved decisions create a new id and
   a supersession relationship. Historical records remain visible.
6. Record titles are descriptive and mutable before approval; identifiers are
   the only cross-reference keys.
7. Placeholders containing `NNNN` are templates, not allocated identifiers.

## 3. Cross-reference scheme

### 3.1 Canonical direction

| Source record | Required references | Conditional references |
| --- | --- | --- |
| Corpus item | Parent corpus id for an artifact beneath an area | Evidence and finding ids discovered from it |
| Evidence item | At least one corpus id | Premise evidence ids, finding ids, superseded/superseding evidence id |
| Finding | Evidence ids and affected corpus ids | Review ids, decision id, related finding ids |
| Review event | Subject id and reviewer role | Evidence considered, resulting status, related decision id |
| Decision | Subject ids, review ids, authority, and rationale | Evidence ids, superseded/superseding decision id, checkpoint id |

The subject record carries forward references during active work. Closure
requires reverse references to be synchronized where the target template
provides them. A missing reverse link is a traceability gap, not a reason to
duplicate the target's content.

### 3.2 Reference syntax

- Use the bare canonical id in fields and prose: `M34-E-NNNN`.
- Use a relative Markdown link when practical, while retaining the id as the
  link label.
- Multiple ids are a lexically sorted, comma-separated list.
- Use `NONE` only when the field is legitimately inapplicable.
- Use `PENDING` when the relationship is required but has not yet been
  established.
- Never use blank text to mean unknown, none, or pending.
- Repository locations use forward slashes and repository-relative paths.
- Symbol, route, section, schema object, command, fixture, or observation
  locator follows the path after `::`.

Canonical locator forms are:

```text
path/to/file.ext
path/to/file.ext::symbol_or_heading
METHOD /route
schema_name.object_name
command::<normalized command label>
runtime::<environment id>::<observation id>
```

Line numbers may be appended as review aids but never replace the stable
locator. External URLs are supporting references only and do not replace an
M34 evidence id.

### 3.3 No cross-reference by implication

Directory proximity, matching titles, identical wording, shared owners, Git
commit adjacency, and chronological order do not establish a relationship.
Every material relationship must be represented by an explicit id.

## 4. Status lifecycle

### 4.1 Corpus item

```text
DECLARED -> DISCOVERED -> VERIFICATION_PENDING
         -> VERIFIED_IN_SCOPE -> COVERAGE_COMPLETE
         -> VERIFIED_OUT_OF_SCOPE
```

`DISPUTED` may be entered from any non-final state. `COVERAGE_COMPLETE` applies
to an area record only after every known in-scope child is registered and its
search bounds are documented. Out-of-scope records remain visible to prevent
repeat discovery.

### 4.2 Evidence item

```text
DRAFT -> CAPTURED -> VERIFIED
                  -> DISPUTED
VERIFIED -> SUPERSEDED
```

`DRAFT` evidence cannot support a finding. `CAPTURED` evidence may support
discovery but not closure. Only `VERIFIED` evidence may support an approved
disposition or readiness decision. `DISPUTED` and `SUPERSEDED` evidence remain
visible and cannot be used as current positive proof.

### 4.3 Finding

The WP1 lifecycle is unchanged:

```text
DRAFT -> VERIFIED -> CLASSIFIED -> IN_ARCHITECTURAL_REVIEW
      -> DISPOSITION_APPROVED -> CLOSED
```

`NEEDS_EVIDENCE`, `DISPUTED`, and `RETURNED_TO_ARB` are permitted branch
states. A closed finding is reopened through a Review Log entry; its prior
status and decision remain recorded.

### 4.4 Review event

Review events are append-only facts and have no mutable lifecycle. Their
outcome is one of:

- `ACKNOWLEDGED`;
- `CHANGE_REQUESTED`;
- `VERIFIED`;
- `APPROVED`;
- `REJECTED`;
- `ESCALATED`;
- `RETURNED`; or
- `CLOSED`.

A correction creates a new review event that references the incorrect event.

### 4.5 Decision

```text
PROPOSED -> UNDER_REVIEW -> APPROVED
                         -> REJECTED
                         -> RETURNED_TO_ARB
APPROVED -> SUPERSEDED
```

Only `APPROVED` decisions govern disposition or readiness. Approved decisions
are immutable. A later change creates a new decision with explicit
`supersedes` and `superseded_by` references.

## 5. Traceability rules

### 5.1 Minimum trace chain

Every closed finding must have an unbroken chain:

```text
Corpus item
    -> verified Evidence item(s)
    -> classified Finding
    -> architectural Review event(s)
    -> approved Decision
    -> closure Review event
```

Every M34 exit decision additionally references all open blocking findings,
all approved exclusions or deferrals, the applicable checkpoint, and the
product-evidence decision. Absence of a finding is never inferred from an
empty link field.

### 5.2 Repository revision and time

- Static repository evidence records the full Git commit hash or the explicit
  dirty-worktree boundary used for capture.
- Runtime and test evidence records the command, environment identity,
  relevant fixture/data boundary, and result.
- All audit timestamps use timezone-aware UTC ISO 8601 with `Z`, for example
  `YYYY-MM-DDTHH:MM:SSZ`.
- Client-local time, file modification time, and Git author time are not audit
  observation time.
- A later repository change does not rewrite earlier evidence. Recapture uses
  a new evidence id when the observed fact materially changes.

### 5.3 Evidence and interpretation

- Observation, interpretation, limitation, and disposition occupy separate
  fields.
- Derived evidence lists every material premise id and a reproducible method.
- Documentation authority and observed behavior are both recorded when they
  differ; neither is silently selected as the winner.
- `UNKNOWN` and `ASSUMPTION` are explicit values and never count as verified
  proof.
- Several incomplete records cannot be combined to manufacture a missing
  owner, semantic definition, timestamp, lineage, or runtime fact.

### 5.4 Ownership and constitutional traceability

- Every finding names exactly one owning domain or `UNKNOWN_OWNERSHIP`.
- Experience records may own rendering defects but cannot be assigned
  ownership of portfolio, ledger, analytics, or market-data truth.
- Each constitutional concern cites the exact governing principle or artifact,
  not merely “architecture.”
- Ownership conflicts and constitutional contradictions use
  `RETURNED_TO_ARB`; auditors do not choose a winner by convenience.

### 5.5 Closure integrity

A record may close only when:

- all required fields contain a value or an explicit `NONE`;
- evidence is verified and not superseded;
- blocking and readiness effects are explicit;
- required domain and architectural reviews are logged;
- the approved decision is linked in both directions;
- closure evidence matches the approved disposition; and
- no unresolved `PENDING` reference remains.

Closure does not mean implementation or repair occurred. It means the audit
record reached its approved disposition honestly.

## 6. Record-editing rules

1. Keep registers human-reviewable Markdown; do not generate a second
   canonical database, spreadsheet, or issue tracker.
2. One detailed block is the canonical record. Do not maintain a manually
   duplicated summary table containing mutable status or decision fields.
3. Before verification, factual corrections may update a draft record and
   must be noted in the Review Log when material.
4. After verification, evidence observations are immutable. Corrections use a
   new evidence id and supersession.
5. After approval, decisions are immutable. Corrections use a new decision id
   and supersession.
6. Finding state and classification may change only with a Review Log event.
7. Review Log entries are append-only.
8. Corpus status changes retain the original inclusion reason and add a review
   reference.
9. Never embed secrets, credentials, tokens, personal information, large
   payloads, or proprietary external content. Record a sanitized locator and
   limitation instead.
10. Never paste implementation proposals into these registers. Dispositions
    identify required outcomes, not code designs.

## 7. Recommended folder structure

```text
docs/implementation/
|-- M34_WP1_charter_and_audit_protocol.md
`-- m34/
    `-- audit/
        |-- README.md
        |-- registers/
        |   |-- corpus_register.md
        |   |-- evidence_register.md
        |   |-- finding_register.md
        |   |-- review_log.md
        |   `-- decision_register.md
        |-- evidence/                 # Create only when evidence collection begins
        |   |-- static/               # Sanitized excerpts or manifests, if needed
        |   |-- runtime/              # Approved non-production observations only
        |   `-- test/                 # Commands and bounded result artifacts
        `-- reports/                  # Later checkpoint and work-package reports
```

`README.md`, `registers/`, and the WP2-WP5 reports under `reports/` now exist.
Supporting `evidence/` directories remain uncreated because the completed work
packages required no separate payload, runtime, or test artifact beyond
canonical register records.

Artifact files stored under a future `evidence/` directory are supporting
material. Their canonical metadata and classification still live in the
Evidence Register. Later reports summarize registers and never replace them.

## 8. Readiness boundary

M34-WP2 through M34-WP5 allocated corpus, evidence, and review ids under this
scheme. They created no finding or decision and did not change M34 readiness.
WP5 returned its authority-dependent handoff to the Architecture Review Board
under the frozen protocol; that return is not an M34 exit decision. M34.1
remains NO-GO until the approved M34 process exits
`READY_FOR_PORTFOLIO_HOME_SLICE`.
