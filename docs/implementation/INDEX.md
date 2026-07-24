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

The latest closed work package is **M41-WP3 — Temporal, Unit, Adjustment, and
Arithmetic Semantics**. Its Architecture and Stage A are approved; Stage B is
confirmed and frozen; and the work package is `COMPLETE`, `CLOSED`, and
`FROZEN`. The canonical closeout is
[M41_WP3_CLOSEOUT.md](M41_WP3_CLOSEOUT.md), and the decision is recorded in
the
[Decision Log](../engineering/DECISION_LOG.md#m41-wp3--temporal-unit-adjustment-and-arithmetic-semantics-closeout).

M41-WP3 closes all normative semantics allocated to it, including the
canonical Golden Vectors `GV-01` through `GV-30`, without granting
implementation, runtime, provider, persistence, API, production, or
executable-validation authority. M41 Architecture, M41-WP1, and M41-WP2
remain complete, confirmed, frozen, and immutable. Result composition and
all other responsibilities allocated to WP4 remain deferred; WP4 may begin
only under separately authorized architecture work.

The earlier closed milestone **M38 — Product Workspace Foundation**
(WP1–WP10), remains complete and frozen; its canonical closeout is
[M38_EPIC_CLOSEOUT.md](M38_EPIC_CLOSEOUT.md), with final decisions in the
[Decision Log](../engineering/DECISION_LOG.md#m38--product-workspace-foundation-epic-closeout).
The M38 document set contains the constitutional WP1 specification, standalone
implementation designs for WP2, WP3, and WP7–WP10, and frozen Decision Log
records for all ten work packages. WP4–WP6 have no standalone files in this
repository; their frozen implementation authorities are represented by their
individual Decision Log entries. Neither closeout recreates or reinterprets
those frozen designs.

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
| M38 | `COMPLETE AND FROZEN` (WP1–WP10); epic closed and ready for merge | [M38_WP1_BOUNDARY_CONTRACT_SPECIFICATION.md](M38_WP1_BOUNDARY_CONTRACT_SPECIFICATION.md) `CAD`; [WP2](M38_WP2_WORKSPACE_CONTEXT_RUNTIME_IMPLEMENTATION_DESIGN.MD), [WP3](M38_WP3_IMPLEMENTATION_DESIGN.md), [WP7](M38_WP7_EXPERIENCE_COMPOSITION_RUNTIME_IMPLEMENTATION_DESIGN.md), [WP8](M38_WP8_EXPERIENCE_OBSERVATION_RUNTIME_IMPLEMENTATION_DESIGN.md), [WP9](M38_WP9_EXPERIENCE_QUERY_RUNTIME_IMPLEMENTATION_DESIGN.md), and [WP10](M38_WP10_DISCOVERY_EXPERIENCE_RUNTIME_IMPLEMENTATION_DESIGN.md) `AIR`; WP4–WP6 are represented by frozen Decision Log records | [M38_EPIC_CLOSEOUT.md](M38_EPIC_CLOSEOUT.md) `CO` | [§M38 Closeout](../engineering/DECISION_LOG.md#m38--product-workspace-foundation-epic-closeout) |
| M39 | `COMPLETE AND FROZEN` (WP1–WP6); constitutional specification corpus, `APPROVED FOR EPIC CLOSEOUT` | [WP1 Canonical Boundary](M39_WP1_Canonical_Boundary_Specification.md) `CAD` (frozen contract); [WP2 Source Boundary](M39_WP2_market_observation_source_boundary_specification.md), [WP3 Classification](M39_WP3_market_observation_classification_specification.md), [WP4 Payload](M39_WP4_market_observation_payload_specification.md), [WP5 Relationship](M39_WP5_market_observation_relationship_specification.md), and [WP6 Identity](M39_WP6_market_observation_identity_specification.md) `CAD` (semantic layers) | [M39_EPIC_CLOSEOUT.md](M39_EPIC_CLOSEOUT.md) `CO` | [§M39 Closeout](../engineering/DECISION_LOG.md#m39--canonical-asset-market-observation-epic-closeout) |
| M40 | Architecture phase complete; WP1 complete, reviewed, and independently confirmed; WP2 `COMPLETE_FOR_INDEPENDENT_CONSTITUTIONAL_REVIEW` with eight `ADMIT` and two `REJECT` decisions; admitted terms are not yet effective because Glossary synchronization and independent approval remain pending; no implementation or runtime authority | [Architecture Plan](M40_Canonical_Asset_Market_Measure_Foundation_Plan.md) `DT`; [Architecture Independent Review](M40_INDEPENDENT_CONSTITUTIONAL_ARCHITECTURE_REVIEW.md) `AU`; [Architecture Review Response](M40_REVIEW_RESPONSE.md) `RCE`; [Architecture Independent Confirmation](M40_INDEPENDENT_CONFIRMATION.md) `AU`; [WP1 Vocabulary and Ownership Specification](M40_WP1_Canonical_Market_Measure_Vocabulary_and_Ownership_Specification.md) `CAD` candidate; [WP1 Independent Review](M40_WP1_INDEPENDENT_REVIEW.md) `AU`; [WP1 Review Response](M40_WP1_REVIEW_RESPONSE.md) `RCE`; [WP1 Independent Confirmation](M40_WP1_INDEPENDENT_CONFIRMATION.md) `AU`; [WP2 Vocabulary Admission Review](M40_WP2_Canonical_Market_Measure_Vocabulary_Admission_Review.md) `RCE` | — | none; not submitted |
| M41-WP1 | `COMPLETE`, `CONFIRMED`, `FROZEN` — Architecture, Stage 1, and Stage 2 (after a two-round Independent Confirmation correction cycle) all independently confirmed | [Architecture Proposal](M41_ARCHITECTURE_PROPOSAL.md) `CAD`; [Stage 1 Register](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md) `CAD`; [Stage 2 Specification](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md) `CAD`; review/confirmation corpus per [M41_WP1_CLOSEOUT.md](M41_WP1_CLOSEOUT.md) | [M41_WP1_CLOSEOUT.md](M41_WP1_CLOSEOUT.md) `CO` | [§M41-WP1 Closeout](../engineering/DECISION_LOG.md#m41-wp1--market-measure-definition-method-version-and-applicability-contract-closeout) |
| M41-WP2 | `COMPLETE`, `CONFIRMED`, `FROZEN` — immutable upstream authority for WP3 | [Architecture Proposal](M41_WP2_ARCHITECTURE_PROPOSAL.md) `CAD`; [Stage A Register](M41_WP2_STAGE_A_CANDIDATE_VOCABULARY_REGISTER.md) `CAD`; [Stage B Specification](M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md) `CAD`; review/confirmation corpus linked from those records | — | not separately indexed |
| M41-WP3 | `COMPLETE`, `CLOSED`, `FROZEN` — Architecture and Stage A approved; Stage B confirmed and frozen after RC-1 resolution; all 30 Golden Vectors canonical | [WP3 Architecture](M41_WP3_ARCHITECTURE_PROPOSAL.md) `CAD`; [Stage A Register](M41_WP3_STAGE_A_VOCABULARY_AND_SEMANTIC_SURFACE_REGISTER.md) `CAD`; [Stage B Specification](M41_WP3_STAGE_B_TEMPORAL_UNIT_ADJUSTMENT_ARITHMETIC_CONTRACT_SPECIFICATION.md) `CAD`; complete review/confirmation corpus per [M41_WP3_CLOSEOUT.md](M41_WP3_CLOSEOUT.md) | [M41_WP3_CLOSEOUT.md](M41_WP3_CLOSEOUT.md) `CO` | [§M41-WP3 Closeout](../engineering/DECISION_LOG.md#m41-wp3--temporal-unit-adjustment-and-arithmetic-semantics-closeout) |

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
- [M38_WP1_BOUNDARY_CONTRACT_SPECIFICATION.md](M38_WP1_BOUNDARY_CONTRACT_SPECIFICATION.md)
- [M38_WP2_WORKSPACE_CONTEXT_RUNTIME_IMPLEMENTATION_DESIGN.MD](M38_WP2_WORKSPACE_CONTEXT_RUNTIME_IMPLEMENTATION_DESIGN.MD)
- [M38_WP3_IMPLEMENTATION_DESIGN.md](M38_WP3_IMPLEMENTATION_DESIGN.md)
- [M38_WP7_EXPERIENCE_COMPOSITION_RUNTIME_IMPLEMENTATION_DESIGN.md](M38_WP7_EXPERIENCE_COMPOSITION_RUNTIME_IMPLEMENTATION_DESIGN.md)
- [M38_WP8_EXPERIENCE_OBSERVATION_RUNTIME_IMPLEMENTATION_DESIGN.md](M38_WP8_EXPERIENCE_OBSERVATION_RUNTIME_IMPLEMENTATION_DESIGN.md)
- [M38_WP9_EXPERIENCE_QUERY_RUNTIME_IMPLEMENTATION_DESIGN.md](M38_WP9_EXPERIENCE_QUERY_RUNTIME_IMPLEMENTATION_DESIGN.md)
- [M38_WP10_DISCOVERY_EXPERIENCE_RUNTIME_IMPLEMENTATION_DESIGN.md](M38_WP10_DISCOVERY_EXPERIENCE_RUNTIME_IMPLEMENTATION_DESIGN.md)
- [M39_WP1_Canonical_Boundary_Specification.md](M39_WP1_Canonical_Boundary_Specification.md)
- [M39_WP2_market_observation_source_boundary_specification.md](M39_WP2_market_observation_source_boundary_specification.md)
- [M39_WP3_market_observation_classification_specification.md](M39_WP3_market_observation_classification_specification.md)
- [M39_WP4_market_observation_payload_specification.md](M39_WP4_market_observation_payload_specification.md)
- [M39_WP5_market_observation_relationship_specification.md](M39_WP5_market_observation_relationship_specification.md)
- [M39_WP6_market_observation_identity_specification.md](M39_WP6_market_observation_identity_specification.md)
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
- [M37_EPIC_CLOSEOUT.md](M37_EPIC_CLOSEOUT.md) — Provider Discovery / UNIVERSE Search; `IMPLEMENTATION COMPLETE` per the [DECISION_LOG.md M37.3 entry](../engineering/DECISION_LOG.md#m373---provider-discovery--universe-search-implementation-closeout)
- [M38_EPIC_CLOSEOUT.md](M38_EPIC_CLOSEOUT.md) — Product Workspace Foundation; WP1–WP10 complete and frozen, implementation review and WP10 remediation closed, ready for merge
- [M39_EPIC_CLOSEOUT.md](M39_EPIC_CLOSEOUT.md) — Canonical Asset Market Observation; WP1–WP6 complete and frozen, `APPROVED FOR EPIC CLOSEOUT` by independent constitutional architecture review, closed 2026-07-23
- [M41_WP1_CLOSEOUT.md](M41_WP1_CLOSEOUT.md) — Market Measure Definition, Method Version, and Applicability Contract; Architecture, Stage 1, and Stage 2 all independently confirmed and frozen, closed 2026-07-23; grants no implementation, runtime, provider, persistence, or API authority
- [M41_WP3_CLOSEOUT.md](M41_WP3_CLOSEOUT.md) — Temporal, Unit, Adjustment, and Arithmetic Semantics; Architecture and Stage A approved, Stage B confirmed and frozen, WP3 closed 2026-07-24; grants no implementation, runtime, provider, persistence, API, production, or executable-validation authority

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
