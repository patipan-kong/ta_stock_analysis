# Implementation Corpus — Navigation Index

This document is **not normative**. It introduces no authority, no
architecture, and no governance of its own. It exists only to help a reader
find the right document quickly. Where this index and any linked document
disagree, the linked document (and ultimately the repository itself) governs.

## Purpose

`docs/implementation/` accumulates one document (or small document set) per
milestone/work package. As the corpus grows, finding "the current canonical
document for X" by directory listing alone gets slower. This index maps each
milestone to its documents, its closeout (if any), and its relationship to
[`docs/engineering/DECISION_LOG.md`](../engineering/DECISION_LOG.md), so a
reader can navigate without re-deriving history from file names and dates.

## Current Milestone Status

The most recently touched milestone in the corpus is **M37 — Universal Asset
Search**. Its own documents declare:

- [M37_WP1_Universal_Asset_Search_Foundation.md](M37_WP1_Universal_Asset_Search_Foundation.md) — `APPROVED_AND_FROZEN`
- [M37_1_Universal_Asset_Search_Technical_Design.md](M37_1_Universal_Asset_Search_Technical_Design.md) — `APPROVED_AND_FROZEN`
- [M37_EPIC_CLOSEOUT.md](M37_EPIC_CLOSEOUT.md) — `IMPLEMENTATION COMPLETE`, per
  [`docs/engineering/DECISION_LOG.md`](../engineering/DECISION_LOG.md#m373---provider-discovery--universe-search-implementation-closeout),
  whose M37.3 entry is committed on `main` (commit `19b0959`, alongside the
  underlying corrections). Commits `8f87915` and `10a6e2d` are both verified
  ancestors of `main`.

Bookkeeping note, not a reopening of implementation verification: as of this
writing, `M37_EPIC_CLOSEOUT.md` itself and the "Closeout:" cross-references
added to the two design documents above are untracked/uncommitted in the
working tree, distinct from the code and Decision-Log entry, which are
committed. This index reports that split as repository evidence; it does not
independently re-adjudicate M37.3's validation numbers.

## Milestone Navigation (M0–current)

| Milestone | Status (as declared in-document) | Primary document(s) | Closeout | Decision Log |
|---|---|---|---|---|
| M0 | Informational (state analysis) | [M0_CURRENT_STATE_ANALYSIS.md](M0_CURRENT_STATE_ANALYSIS.md) `AU` | — | not indexed by milestone number |
| M5 Track B | Historical; §8 superseded by M9 | [M5_TRACK_B_NATIVE_INTEGRATION_TDD.md](M5_TRACK_B_NATIVE_INTEGRATION_TDD.md) `CAD`, [M5_TRACK_B_STAGE2_RUNBOOK.md](M5_TRACK_B_STAGE2_RUNBOOK.md) `AIR` | — | not indexed by milestone number |
| M6 | Migration report; step 8 superseded | [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) `AIR` | — | not indexed by milestone number |
| M9 | Ratified; supersedes M5 Track B §8 | [M9_ASSET_DEFINITION_RUNTIME_TDD.md](M9_ASSET_DEFINITION_RUNTIME_TDD.md) `CAD` | — | not indexed by milestone number |
| M22–M28 | Complete (vocabulary/definition authoring) | not present in `docs/implementation/` | — | [§M22](../engineering/DECISION_LOG.md#m22--fund-canonical-definition-authoring)–[§M28](../engineering/DECISION_LOG.md#m28--asset-scope-governance-review) |
| M29 | Audit only; no production code changed | [portfolio_runtime_adoption.md](portfolio_runtime_adoption.md) `AU` | — | [§M29](../engineering/DECISION_LOG.md#m29--portfolio-runtime-adoption-audit) |
| M30 (design) | Design only, no code | [M30_capability_safety_foundation_design.md](M30_capability_safety_foundation_design.md) `DES` | — | [§M30](../engineering/DECISION_LOG.md#m30--capability-safety-foundation-technical-design) |
| M30.1–M30.3 | Implemented, adopted, fanned out | no dedicated document in this directory | — | [§M30.1](../engineering/DECISION_LOG.md#m301--capability-safety-foundation-implementation)–[§M30.3](../engineering/DECISION_LOG.md#m303--capability-safety-adoption-portfolio-fan-out) |
| M31.1–M31.3 | Shadow adoption stages | no dedicated document in this directory | — | [§M31.1](../engineering/DECISION_LOG.md#m311---execution-instrument-facts-foundation)–[§M31.3](../engineering/DECISION_LOG.md#m313---execution-eligibility-shadow-adoption) |
| M31.4 | Readiness audit and design | [M31_4_execution_cutover_readiness.md](M31_4_execution_cutover_readiness.md) `AU`/`DES` | — | not indexed by milestone number |
| M31.5 | Preparation complete; cutover **NO-GO** | [M31_5_registry_cutover_preparation.md](M31_5_registry_cutover_preparation.md) `AIR` | — | [§M31.5](../engineering/DECISION_LOG.md#m315---execution-registry-cutover-preparation) |
| M31.6 | `LEGACY_FALLBACK`; enforcement not yet reached | [M31_6_registry_remediation_wave1.md](M31_6_registry_remediation_wave1.md) `AIR` (+ manifest/preflight JSON) | — | [§M31.6](../engineering/DECISION_LOG.md#m316---registry-remediation-wave-1) |
| M32 (full arc) | Closed; governance closeout, not full cutover | [M32_cost_aware_execution_planning_design.md](M32_cost_aware_execution_planning_design.md) `CAD`, M32.1–M32.3E3 sub-milestone documents (see directory listing) `AIR`/`DES` | [M32_EPIC_CLOSEOUT.md](M32_EPIC_CLOSEOUT.md) `CO` | [§M32.1](../engineering/DECISION_LOG.md#m321---versioned-feequote-foundation-and-ledger-parity)–[§M32 Closeout](../engineering/DECISION_LOG.md#m32--cost-aware-execution-planning-epic-closeout) |
| M33.1–M33.11 | Mixed: design-complete, implemented, and complete/POC entries per sub-milestone | M33_1…M33_11 documents (see directory listing) `CAD`/`AIR`/`DES` | none present | [§M33.1](../engineering/DECISION_LOG.md#m331---execution-intent-snapshot-and-lifecycle-foundation)–[§M33.11](../engineering/DECISION_LOG.md#m3311---supabase-auth-security-state-and-assurance-proof-of-concept) |
| M34 | **Mixed — see below** | [M34_WP1_charter_and_audit_protocol.md](M34_WP1_charter_and_audit_protocol.md) `CAD`, [m34/audit/](m34/audit/) `AIR` (README, registers, reports) | [M34_WP6A_governance_closeout.md](m34/audit/reports/M34_WP6A_governance_closeout.md) `CO` (WP6A only) | [§M34-WP6A](../engineering/DECISION_LOG.md#m34-wp6a---post-arb-semantic-governance-production) |
| M35 | `PROPOSED_FOR_SECOND_ARCHITECTURAL_REVIEW` (WP1); `COMPLETE_FOR_SECOND_ARCHITECTURAL_REVIEW` (WP2) | [M35_WP1_Product_Workspace_Foundation.md](M35_WP1_Product_Workspace_Foundation.md) `CAD`, [M35_WP2_Architectural_Remediation_Summary.md](M35_WP2_Architectural_Remediation_Summary.md) `RCE` | none present | not indexed by milestone number |
| M36 | `M36-WP1`: `APPROVED_AND_CANONICAL`, closed. `M36.1`: `PROPOSED_FOR_IMPLEMENTATION` — **requires reconciliation** against WP1's closed/canonical status before being treated as settled | [M36_WP1_Multiple_Portfolio_Foundation.md](M36_WP1_Multiple_Portfolio_Foundation.md) `CAD`, [M36_1_Runtime_Foundation.md](M36_1_Runtime_Foundation.md) `DT`, [M36_WP2_Architectural_Remediation_Summary.md](M36_WP2_Architectural_Remediation_Summary.md) `RCE` | [M36_EPIC_CLOSEOUT.md](M36_EPIC_CLOSEOUT.md) `CO` | [§M36 Closeout](../engineering/DECISION_LOG.md#m36---multiple-portfolio-foundation-closeout) |
| M37 | `APPROVED_AND_FROZEN` (design docs); `IMPLEMENTATION COMPLETE` (Decision Log, committed) | [M37_WP1_Universal_Asset_Search_Foundation.md](M37_WP1_Universal_Asset_Search_Foundation.md) `CAD`, [M37_1_Universal_Asset_Search_Technical_Design.md](M37_1_Universal_Asset_Search_Technical_Design.md) `CAD` | [M37_EPIC_CLOSEOUT.md](M37_EPIC_CLOSEOUT.md) `CO` | [§M37.3 Closeout](../engineering/DECISION_LOG.md#m373---provider-discovery--universe-search-implementation-closeout) |

**M34 status detail** (a single "Complete" label does not hold for the whole
milestone — its two governance tracks diverge):

- **M34-WP6A** (semantic governance production) — work package status `CLOSED`.
  Per [M34_WP6A_governance_closeout.md](m34/audit/reports/M34_WP6A_governance_closeout.md) §5–6: *"Authorization: None. WP6 remains `WP6_BLOCKED`. M34.1 remains `NO-GO`."*
- **M34-WP6** (the authorization gate itself, tracked separately from WP6A) —
  submission package `M34-WP6-ASP-0001` v0.2.0 is in lifecycle state
  `RETURNED`; return decision `M34-WP6-ASP-0006` requires outcome
  `CORRECTION_BLOCKED`. See
  [M34_WP6_administrative_return_closure_plan.md](m34/audit/reports/M34_WP6_administrative_return_closure_plan.md).
  No corrected successor package exists yet.

## Canonical Documents

Design-of-record documents currently in force (`APPROVED_AND_FROZEN`,
`APPROVED_AND_CANONICAL`, or an equivalent in-document status), superseding
any earlier draft of the same subject:

- [M9_ASSET_DEFINITION_RUNTIME_TDD.md](M9_ASSET_DEFINITION_RUNTIME_TDD.md)
- [M32_cost_aware_execution_planning_design.md](M32_cost_aware_execution_planning_design.md)
- [M34_WP1_charter_and_audit_protocol.md](M34_WP1_charter_and_audit_protocol.md)
- [M36_WP1_Multiple_Portfolio_Foundation.md](M36_WP1_Multiple_Portfolio_Foundation.md)
- [M37_WP1_Universal_Asset_Search_Foundation.md](M37_WP1_Universal_Asset_Search_Foundation.md)
- [M37_1_Universal_Asset_Search_Technical_Design.md](M37_1_Universal_Asset_Search_Technical_Design.md)
- [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](ASSET_REGISTRY_IMPLEMENTATION_PLAN.md) (Status: Complete, 2026-07-09)

[M36_1_Runtime_Foundation.md](M36_1_Runtime_Foundation.md) is deliberately
excluded from this list: its own in-file status is `PROPOSED_FOR_IMPLEMENTATION`,
not approved/canonical, and it is not yet reconciled with `M36-WP1`'s
`APPROVED_AND_CANONICAL` status covering the same milestone number. See the
M36 row in the navigation table above.

Broader architecture documents (not milestone-scoped) live under
[docs/architecture/](../architecture/), not here — see that directory's own
`README.md` for its navigation.

## Closeout Documents

- [M32_EPIC_CLOSEOUT.md](M32_EPIC_CLOSEOUT.md) — Cost-aware Execution Planning; closed 2026-07-15, governance closeout (not a full cutover declaration)
- [M36_EPIC_CLOSEOUT.md](M36_EPIC_CLOSEOUT.md) — Multiple Portfolio Foundation; closed 2026-07-20, canonical
- [M37_EPIC_CLOSEOUT.md](M37_EPIC_CLOSEOUT.md) — Provider Discovery / UNIVERSE Search; `IMPLEMENTATION COMPLETE` per the committed [DECISION_LOG.md M37.3 entry](../engineering/DECISION_LOG.md#m373---provider-discovery--universe-search-implementation-closeout); the closeout file itself is currently untracked (see Current Milestone Status above)

## Active Governance

- [m34/audit/](m34/audit/) — README, registers/, reports/: the live M34 audit corpus referenced by the DECISION_LOG's M34-WP6A entry
- [docs/decisions/](../decisions/) — ADR-001 through ADR-006, each independent of milestone numbering; ADR-006 specifically governs M34's external-governance dependency
- [docs/engineering/DECISION_LOG.md](../engineering/DECISION_LOG.md) — the single chronological authority for what shipped and when; this index only points into it, never restates its entries

## Historical Milestones

Documents whose successor has already superseded them, kept for lineage:

- [M5_TRACK_B_NATIVE_INTEGRATION_TDD.md](M5_TRACK_B_NATIVE_INTEGRATION_TDD.md) — §8 superseded by [M9_ASSET_DEFINITION_RUNTIME_TDD.md](M9_ASSET_DEFINITION_RUNTIME_TDD.md)
- [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) — step 8 superseded by its own Phase 4 Migration Report section
- [CLASSIFICATION_CONSOLIDATION.md](CLASSIFICATION_CONSOLIDATION.md) — historical-alias handling folded into later Registry documents

## Archive Candidates (informational only)

**No archival of any document in this directory is currently authorized by
this index or by any other document it links to.** The list below is a
narrower, evidence-checked set than an earlier draft of this index carried;
entries were removed where repository evidence did not conclusively support
relocation:

- M32.3-series sub-documents (`M32_3A`…`M32_3E3S2`) — intermediate shadow/design
  stages whose outcomes are accounted for in [M32_EPIC_CLOSEOUT.md](M32_EPIC_CLOSEOUT.md),
  itself a closed governance closeout dated 2026-07-15.

Removed from this list on evidence grounds (not archive candidates):

- **M31.5 / M31.6** — [M31_5_registry_cutover_preparation.md](M31_5_registry_cutover_preparation.md)
  declares cutover **`NO-GO`**, and [M31_6_registry_remediation_wave1.md](M31_6_registry_remediation_wave1.md)
  declares cutover status `LEGACY_FALLBACK`. Neither document's own governing
  cutover is closed; M32's closeout addresses cost-aware execution planning,
  not the M31 registry-cutover decision itself. Retained as active.
- **[WATCHLIST_REGISTRY_PILOT.md](WATCHLIST_REGISTRY_PILOT.md)** — actively
  referenced by at least seven other documents in this repository, including
  [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](ASSET_REGISTRY_IMPLEMENTATION_PLAN.md),
  [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md),
  [CLASSIFICATION_CONSOLIDATION.md](CLASSIFICATION_CONSOLIDATION.md), and two
  `docs/architecture/` documents, plus M34-WP6 authorization submission
  materials. An earlier draft of this index asserted "no active consumer
  references it," which a repository grep directly contradicts. Retained as
  active; classified `U` (unclear) rather than archived, since its own
  lifecycle status is not restated by any of its referencing documents.

## Classification Legend

| Code | Meaning |
|---|---|
| `CAD` | Canonical architecture/design — the design of record for its subject |
| `IA` | Implementation authority — a document whose primary function is granting, recording, or returning authorization to implement (e.g. an authorization-gate decision, a governance closeout that states an authorization outcome) |
| `AIR` | Active implementation record — documents code that shipped, or an in-progress audit/review corpus still being maintained |
| `RCE` | Review/conformance evidence — independent-review or architectural-remediation output produced in response to a review cycle |
| `CO` | Closeout record — an epic/milestone/work-package closeout report |
| `SS` | Superseded — an earlier document (or section of one) whose content has been replaced by a named successor |
| `DT` | Draft/template — proposed, not yet approved; a `PROPOSED_FOR_...`-style in-file status |
| `U` | Unclear — this index cannot state a settled lifecycle status from repository evidence alone |

Two additional codes are retained from an earlier revision of this index.
They do not redefine any code above, per the constraint that additional
navigation-only codes may only be kept if they don't conflict with the
primary eight:

| Code | Meaning |
|---|---|
| `AU` | Audit — read-only analysis; no production code changed |
| `DES` | Design only — no implementation exists yet for this document |

Codes are assigned by this index for navigation purposes only; a document's
own in-file status line (e.g. `APPROVED_AND_FROZEN`, `PROPOSED_FOR_...`) is
always the authoritative statement of its state, not the code shown here.
