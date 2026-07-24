# M41-WP2 Stage A - Independent Review

**Document role:** Independent Architecture Review Board

**Review target:** [M41-WP2 Stage A Candidate Vocabulary Register](M41_WP2_STAGE_A_CANDIDATE_VOCABULARY_REGISTER.md)

**Date:** 2026-07-23

**Architecture authority:** Frozen and cited, not modified

**M41-WP1 authority:** Frozen and cited, not modified

**M41-WP2 Architecture authority:** Frozen and cited, not modified

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API authority:** `NONE`

---

## Executive Summary

The Stage A register correctly limits evaluation to the three candidates
required by the confirmed WP2 Architecture, preserves the frozen M41/WP1
contract boundaries, and does not begin Stage B. Its analyses support
`MERGE` for Subject Reference and Subject Ordering Key, and support `ADMIT`
for Manifest Entry without widening the frozen M40 Observation Input Manifest
membership beyond exact M39 Observation evidence.

One required governance correction remains. The confirmed WP2 Architecture
requires every candidate entry to record a determined single owner through
the Stage A candidate-admission workflow. The two `MERGE` entries instead
record their proposed owner as absent. Their narrative identifies the
existing canonical owners, but the required ownership disposition is not
recorded as such.

## Review Scope

This review assesses only the Stage A Candidate Vocabulary Register against
the confirmed M41 Architecture, confirmed WP1 Stage 1 and Stage 2 authority,
and the confirmed M41-WP2 Architecture Proposal. It does not redesign the
architecture, perform Stage B work, or change any frozen artifact.

## Candidate Assessment

| Candidate | Recommended Disposition | Status | Notes |
|---|---|---|---|
| Subject Reference | `MERGE` | Conditionally supported | The definition properly collapses into Asset Foundation's existing immutable `asset_id`, cited by Measure Subject; it avoids a provider-shaped shadow identity. The record must nevertheless state Asset Foundation as the determined existing owner and record the no-new-ownership `MERGE` disposition. |
| Subject Ordering Key | `MERGE` | Conditionally supported | The definition properly remains an ordering-rule field of the confirmed Market-Intelligence-owned Measure Subject, rather than a new canonical noun. The record must state Market Intelligence as the determined existing owner and record the no-new-ownership `MERGE` disposition. |
| Manifest Entry | `ADMIT` | Supported | The proposed definition, Market Intelligence ownership, glossary and canonical-overlap analysis, M39/M40 boundary, negative-corpus analysis, V1/V2/V3 analysis, M34 compatibility, and five-part gate are complete. The entry is limited to one exact frozen M39 Observation reference plus its declared prerequisite-evaluation role; it excludes Asset Foundation reference data, invocation parameters, and governed calculation dependencies. |

The register's conclusion that no additional governed vocabulary candidate is
required is supported. It correctly retains Manifest Identity, Canonical
Serialization, Evidence Equivalence, and Evidence Conflict Determination as
the ordinary non-canonical contract language already settled by WP1 Stage 1.

## Findings

### M41-WP2-SA-IR-1 - Ownership disposition absent for the two `MERGE` candidates

**Issue:** Subject Reference and Subject Ordering Key each state that no
owner is proposed and show `N/A` as their ownership rationale. The summary
and validation sections repeat that no owner is proposed for either entry.

**Rationale:** The confirmed WP2 Architecture Proposal section 11 requires
each Stage A candidate entry to contain a determined single owner, justified
through the governed candidate-admission workflow and recorded as a Stage A
ownership disposition. A `MERGE` produces no new ownership, but it must
identify the sole existing owner into which the candidate's meaning merges.
Narrative references to Asset Foundation's `asset_id` and
Market-Intelligence-owned Measure Subject do not substitute for the required
recorded disposition.

**Governing authority:** M41 Architecture Proposal section 8
(candidate-vocabulary admission workflow) and confirmed M41-WP2 Architecture
Proposal section 11 (Stage A deliverables and ownership singularity).

## Required Corrections

### M41-WP2-SA-IR-1

For each `MERGE` record, replace the absent proposed-owner/`N/A` treatment
with an explicit Stage A ownership disposition that records the sole existing
canonical owner and confirms no ownership transfer or new canonical noun:

- Subject Reference: Asset Foundation, through the existing `asset_id` cited
  by Measure Subject.
- Subject Ordering Key: Market Intelligence, through the confirmed Measure
  Subject ordering obligation.

Update the disposition summary and validation statements to match those two
recorded ownership dispositions. This correction is local to the Stage A
register and does not modify the merged canonical terms, admit either
candidate, or alter any frozen authority.

## Repository Validation

- The review found no tracked modification to the M41 Architecture, WP1
  artifacts, `docs/GLOSSARY.md`, `docs/engineering/DECISION_LOG.md`,
  `docs/implementation/INDEX.md`, or `graphify-out/`.
- No Stage B artifact exists. No prior Stage A review, correction-response, or
  confirmation artifact existed before this review document was created.
- The target register declares implementation, runtime, provider,
  persistence, and API authority `NONE`.
- The register does not modify the Glossary, Decision Log, Implementation
  Index, or Graphify, and it provides no implementation or runtime artifact.
- `git diff --check` completed without reported whitespace errors. The
  repository contains the M41-WP2 governance documents as untracked work;
  this review does not alter them.

## Final Determination

APPROVED WITH REQUIRED CORRECTIONS
