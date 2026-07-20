# M34-WP6A - Vocabulary Synchronization

**Date:** 2026-07-19

**Status:** Complete synchronization record for the post-ARB vocabulary
production. Independent Review Log approval and the WP6 checkpoint remain
separate dependencies.

**Current gate:** WP6 remains unauthorized under `M34-D-0012`. M34.1 remains
NO-GO.

## 1. Authoritative synchronization direction

```text
docs/GLOSSARY.md
  canonical platform vocabulary
          |
          v
docs/architecture/platform_architecture.md
  unchanged constitutional owner and dependency boundaries
          |
          v
M34-D-0001 through M34-D-0012
  approved ARB concept, owner, constraint, and gate rulings
          |
          v
M34_WP6A_DQ01_claim_family_owner_mapping.md
M34_WP6A_semantic_mapping.md
  claim-specific interpretation, decomposition, and provenance
          |
          v
WP6_INCLUDED / WP6_EXCLUDED
  DQ-06 claim-family admission only
```

The arrows express governance dependency, not permission for a downstream
artifact to redefine an upstream one. The Glossary is the only canonical
vocabulary. Platform Architecture is unchanged and remains constitutionally
superior at domain boundaries. Decision Records govern the M34 application of
those boundaries. Mappings transcribe the decisions. Admission consumes the
effective results and owns none of their semantics.

## 2. Synchronization matrix

| ARB source | Canonical Glossary entries | Constitutional boundary retained | Decision Record | Semantic mapping | WP6 admission effect |
| --- | --- | --- | --- | --- | --- |
| DQ-02 | Portfolio Identity; Accounting Scope; Portfolio Strategy Metadata; Goal Target; Current Selection | Ledger & Accounting; Portfolio Intelligence; Wealth Intelligence; Experience Platform | `M34-D-0002` | Sections 2 and 11 | `SA01` requires the complete decomposition |
| DQ-03 | Portfolio Membership; Cross-Portfolio Aggregation; Cross-Portfolio Exposure | Ledger & Accounting; Wealth Intelligence | `M34-D-0003` | Sections 3 and 11 | `SA02` requires scope provenance and the complete decomposition |
| DQ-04 | Asset Classification; Market Classification Evidence; Analytical Grouping | Asset Foundation; Market Intelligence; Portfolio Intelligence in the approved M34 contexts | `M34-D-0004` | Sections 4 and 11 | Sector-dependent claims require explicit classification/grouping provenance |
| DQ-05 | Canonical Temporal Claim; Event Type; Producing Domain; Degraded State; Presentation Label | Every producing domain; Experience presentation only | `M34-D-0005` | Sections 5 and 11 | Every admitted time-bearing claim requires the full temporal tuple |
| DQ-07 | Portfolio Strategy Metadata; Goal Target; Decision Policy; Portfolio Limits; Sector Limits; Persona; Model Selection; Analysis Source Selection; Optimizer Configuration | Portfolio Intelligence; Wealth Intelligence; Decision Intelligence; context-bound producing/consuming domains | `M34-D-0007` | Sections 6 and 11 | `SA25` and `SA39` require family decomposition and concrete context-bound owner bindings |
| DQ-08 | Execution Plan Projection; Legacy Decision Record; `STOPPED_AUTHORITY`; Execution Detail; Plan-versus-Actual Comparison; Decision Memory | M32/M33 stop boundary; Ledger & Accounting facts; Trust & Evaluation comparison; Decision Intelligence-owned Decision Memory composition under `M34-D-0001` | `M34-D-0008` | Section 7 | `SA27` and `SA28` remain excluded; `SA29` admits only Plan-versus-Actual Comparison and Ledger facts, and `SA30` admits only Decision Memory. Execution Detail and Legacy Decision Record remain outside every included verification contract |
| DQ-09 | Portfolio Status; Goal Status; Market Context Status; Optimizer Status; Policy Status; Station Health; Committee Status; Translation Status; Action Required | Source constitutional domains; Trust & Evaluation independent; Experience composition only | `M34-D-0009` | Sections 8 and 11 | `SA36` and operational `SA37` require source owner, temporal tuple, and provenance |
| DQ-10 | Market Observation; Investment Judgment; Instrument-Level Risk; Consensus; Analysis History; Evaluation | Asset Foundation; Market Intelligence; Decision Intelligence; Trust & Evaluation; Experience presentation only | `M34-D-0010` | Sections 9 and 11 | `SA20` and `SA21` require the complete decomposition |
| DQ-11 | Watchlist Membership; User Preference State; Interaction State | Experience Platform for interaction only; all adjacent truth remains with source domains | `M34-D-0011` | Sections 10 and 11 | `SA38` may verify interaction semantics only |

`M34-D-0001` governs the claim-family owner-name interpretation used by every
row. `M34-D-0006` governs bounded vocabulary admission. `M34-D-0012` keeps
the gate closed until all required artifacts are completed and independently
reviewed.

## 3. Term-level coverage manifest

The canonical additions are exactly:

### DQ-02

- Portfolio Identity
- Accounting Scope
- Portfolio Strategy Metadata
- Goal Target
- Current Selection

### DQ-03

- Portfolio Membership
- Cross-Portfolio Aggregation
- Cross-Portfolio Exposure

### DQ-04

- Asset Classification
- Market Classification Evidence
- Analytical Grouping

### DQ-05

- Canonical Temporal Claim
- Event Type
- Producing Domain
- Degraded State
- Presentation Label

### DQ-07

- Decision Policy
- Portfolio Limits
- Sector Limits
- Persona
- Model Selection
- Analysis Source Selection
- Optimizer Configuration

Portfolio Strategy Metadata and Goal Target are reused from DQ-02 without
creating duplicate entries.

### DQ-08

- Execution Plan Projection
- Legacy Decision Record
- `STOPPED_AUTHORITY`
- Execution Detail
- Plan-versus-Actual Comparison
- Decision Memory

### DQ-09

- Portfolio Status
- Goal Status
- Market Context Status
- Optimizer Status
- Policy Status
- Station Health
- Committee Status
- Translation Status
- Action Required

### DQ-10

- Market Observation
- Investment Judgment
- Instrument-Level Risk
- Consensus
- Analysis History
- Evaluation

Asset identity and classification reuse the pre-existing Asset entry and the
DQ-04 Asset Classification entry.

### DQ-11

- Watchlist Membership
- User Preference State
- Interaction State

## 4. Platform Architecture consistency

No Platform Architecture text is changed. The synchronization preserves its
existing laws:

- Asset Foundation owns identity and canonical classification.
- Market Intelligence owns market observations and provider evidence.
- Ledger & Accounting owns financial facts and accounting scope.
- Portfolio Intelligence owns portfolio-derived meaning.
- Decision Intelligence owns investment judgments, recommendations, and
  policy.
- Trust & Evaluation evaluates independently and remains non-operational.
- Wealth Intelligence owns cross-portfolio and goal meaning.
- Experience Platform owns presentation and the bounded interaction concepts
  explicitly approved by the ARB.

Context-bound glossary entries do not create floating authority. Model
Selection, Analysis Source Selection, Station Health, Committee Status, and
Translation Status require one concrete constitutional owner binding before
their associated claim can enter WP6.

Persona and presentation compositions have no independent business-rule
authority; every referenced semantic concept retains its owner.

## 5. Decision and mapping consistency

| Required relationship | Synchronized artifact |
| --- | --- |
| WP1 labels are historical, not constitutional aliases | `M34-D-0001`; `M34_WP6A_DQ01_claim_family_owner_mapping.md` |
| Approved decompositions and ownership | `M34-D-0002` through `M34-D-0005`, `M34-D-0007` through `M34-D-0011`; `M34_WP6A_semantic_mapping.md` |
| Canonical vocabulary is the only vocabulary authority | `docs/GLOSSARY.md`; `M34-D-0006` |
| Legacy authority remains stopped | `M34-D-0008`; `STOPPED_AUTHORITY` Glossary entry |
| SA27/SA28 admission remains deferred | `M34-R-0019`; `M34_WP6A_wp6_admission_manifest.md` |
| WP6 remains closed pending effective governance | `M34-D-0012` |
| Project-level decision trace | `docs/engineering/DECISION_LOG.md::M34-WP6A - Post-ARB Semantic Governance Production` |

## 6. WP6 consumption rule

A claim family may be listed in `WP6_INCLUDED` only when:

1. its approved semantic concepts and owners are present in the mapping;
2. every canonical term used by its verification contract exists in the
   Glossary;
3. every context-bound owner is concretely named;
4. its required provenance and temporal qualifiers are explicit;
5. its allowed positive or negative verification scope is explicit; and
6. independent review confirms the artifacts are synchronized.

An ownerless or excluded concept may appear only as opaque excluded evidence.
It cannot enter an included family's effective vocabulary, verification
subject, semantic provenance, lifecycle semantics, or negative-guarantee
scope. In particular, `SA29` does not admit Execution Detail and `SA30` does
not admit Legacy Decision Record.

Otherwise the family belongs in `WP6_EXCLUDED` with its missing artifact,
owner, remaining governance work, and readiness consequence.

## 7. Non-amendment statement

This synchronization record does not:

- modify Platform Architecture or a Domain Constitution;
- reinterpret an ARB decision;
- alter frozen WP1-WP5A evidence;
- create another canonical vocabulary;
- approve itself independently;
- authorize WP6, M34.1, Portfolio Home, implementation, or runtime work; or
- reopen M32 or M33.

Independent Review Log approval and a checkpoint remain required. WP6 is
unauthorized. M34.1 remains NO-GO.
