# M34-WP6A - Approved Semantic Mapping

**Date:** 2026-07-19

**Status:** Complete canonical post-ARB semantic mapping. It transcribes the
approved decompositions, ownership, provenance, composite boundaries, and
presentation boundaries in `M34-D-0001` through `M34-D-0011` without changing
their meaning.

**Current gate:** WP6 remains unauthorized under `M34-D-0012`. This mapping
does not admit a claim family. M34.1 remains NO-GO.

## 1. Mapping laws

1. One semantic concept has exactly one constitutional owner.
2. Inputs retain their source-domain ownership when consumed downstream.
3. A route, service, table, cache, transport type, persistence field,
   aggregator, or presentation cannot acquire semantic authority by carrying
   a value.
4. Experience Platform owns the interaction concepts expressly assigned by
   the ARB and presentation behavior only; it owns no source-domain truth.
5. A reference composition owns none of the independently owned concepts it
   references.
6. Context-bound owner rules must resolve to one named constitutional domain
   for each concrete setting or status before that item enters WP6.
7. All authoritative temporal claims use `M34-D-0005`.
8. All legacy execution and decision claims use `M34-D-0008`.

## 2. Portfolio identity and scope decomposition

| Concept | Constitutional owner | Meaning | Provenance and boundary | Decision |
| --- | --- | --- | --- | --- |
| Portfolio Identity | Ledger & Accounting | Stable identifier for one portfolio container | Establishes accounting identity only | `M34-D-0002` |
| Accounting Scope | Ledger & Accounting | Boundary to which holdings, transactions, and balances belong | Every decomposed Portfolio concept references this same scope | `M34-D-0002` |
| Portfolio Strategy Metadata | Portfolio Intelligence | Metadata describing the portfolio as an investment-strategy container | Excludes goals, decision policy, and accounting truth | `M34-D-0002`, `M34-D-0007` |
| Goal Target | Wealth Intelligence | Desired investment or financial objective and intended outcome | Referenced by strategy and policy; owned by neither | `M34-D-0002`, `M34-D-0007` |
| Current Selection | Experience Platform | UI state naming the portfolio currently being viewed | Has no business meaning and cannot redefine Accounting Scope | `M34-D-0002` |

**Invariant:** Decomposition changes semantic ownership only. It never divides
or redefines the Ledger-owned accounting identity.

## 3. Cross-portfolio decomposition

| Concept | Constitutional owner | Meaning | Provenance and boundary | Decision |
| --- | --- | --- | --- | --- |
| Portfolio Membership | Ledger & Accounting | Membership of a holding or instrument in one or more Accounting Scopes | Accounting fact, not investment interpretation | `M34-D-0003` |
| Cross-Portfolio Aggregation | Ledger & Accounting | Mathematical aggregation of holdings across Accounting Scopes | Adds no investment meaning | `M34-D-0003` |
| Cross-Portfolio Exposure | Wealth Intelligence | Interpretation of aggregated holdings as overall exposure | Retains every contributing Accounting Scope plus Market and Asset inputs | `M34-D-0003` |

**Composite boundary:** A cross-portfolio presentation owns none of these
concepts. Portfolio Intelligence and Experience Platform do not own
Cross-Portfolio Exposure.

## 4. Classification and analytical-grouping decomposition

| Concept | Constitutional owner or binding | Meaning | Provenance and boundary | Decision |
| --- | --- | --- | --- | --- |
| Canonical Asset Classification | Asset Foundation | Authoritative classification assigned to an Asset | Canonical platform truth | `M34-D-0004` |
| Market Classification Evidence | Market Intelligence | Provider-supplied metadata supporting classification | Evidence only; never canonical by receipt or storage | `M34-D-0004` |
| Classification Projection | Source owner remains Asset Foundation | Stored, transported, cached, or displayed representation of canonical classification | No independent authority; must trace to canonical classification | `M34-D-0004` |
| Analytical Grouping | Portfolio Intelligence for the M34 portfolio-analysis contexts mapped by `M34-D-0001` | Context-specific grouping for portfolio analysis, allocation, factors, attribution, reporting, or visualization | Distinct from canonical classification; Experience may visualize but not define it | `M34-D-0001`, `M34-D-0004` |

**Invariant:** Every sector-related value declares which of the four rows it
represents. Similar wording never establishes semantic identity.

## 5. Canonical temporal and degraded-state mapping

Every authoritative time statement is the tuple:

```text
TemporalClaim(
  event_type,
  producing_domain,
  timestamp,
  degraded_state
)
```

| Element | Owner | Canonical meaning |
| --- | --- | --- |
| Event Type | Producing constitutional domain | Material event being dated: Observation, Retrieval, Calculation, Analysis Generation, Snapshot Creation, Batch Evaluation, or Synchronization |
| Producing Domain | The named constitutional domain | Domain that owns the event and degraded-state semantics |
| Timestamp | Producing constitutional domain | Authoritative time of the named event |
| Degraded State | Producing constitutional domain | `UNKNOWN`, `UNAVAILABLE`, `DELAYED`, `STALE`, `PARTIAL`, or `CONFLICTING` under that domain's contract |
| Presentation Label | Experience Platform | Non-normative rendering such as `Updated`, `As Of`, `Current`, or `Fresh`; cannot replace the authoritative tuple |

Client refresh, cache refresh, polling, rendering completion, and interaction
events cannot redefine source freshness. Decision: `M34-D-0005`.

## 6. Configuration-family decomposition

| Concept | Constitutional owner or binding | Meaning | Reference boundary | Decision |
| --- | --- | --- | --- | --- |
| Portfolio Strategy Metadata | Portfolio Intelligence | Strategy-container metadata | References but does not own Goal Target or Decision Policy | `M34-D-0007` |
| Goal Target | Wealth Intelligence | Desired objective or outcome | Independent from strategy metadata | `M34-D-0007` |
| Decision Policy | Decision Intelligence | Policy envelopes, optimization rules, constraints, execution preferences, and optimizer behavior | Consumes referenced goals and strategy metadata | `M34-D-0007` |
| Portfolio Limits | Decision Intelligence | Constraints on composition and optimization | Governs decision behavior, not identity | `M34-D-0007` |
| Sector Limits | Decision Intelligence | Constraints referencing Canonical Asset Classification | Does not redefine Asset Foundation classification | `M34-D-0004`, `M34-D-0007` |
| Model Selection | Exactly one producing constitutional domain per concrete model setting | Selection of an analytical or decision model governing that domain's behavior | No platform-wide configuration authority | `M34-D-0007` |
| Analysis Source Selection | Exactly one consuming constitutional domain per concrete source setting | Selection of data or analytical sources consumed by that domain | Does not own underlying source data | `M34-D-0007` |
| Optimizer Configuration | Decision Intelligence | Optimizer-layer orchestration and fallback behavior | Governs optimizer behavior only | `M34-D-0007` |
| Persona | No independent business-rule owner; reference composition only | Bounded preset referencing independently owned settings | Cannot become Strategy Metadata, Goal Target, or Decision Policy | `M34-D-0007` |

**Owner-binding condition:** A concrete Model Selection or Analysis Source
Selection record is not owner-verifiable until its producing or consuming
constitutional domain is named. Persona is not an independently authoritative
business concept.

## 7. Legacy `STOPPED_AUTHORITY` mapping

| Concept | Record-domain context | Permitted meaning | Explicit non-authority | Decision |
| --- | --- | --- | --- | --- |
| Execution Plan Projection | Legacy Decision Intelligence presentation | Historical projection presented by the legacy workflow | Not a canonical plan, approved intent, instruction, or authorization | `M34-D-0008` |
| Legacy Decision Record | Legacy application record | Proof only that the application stored a decision-related record | No approval, actor identity, decision authority, or constitutional authorization | `M34-D-0008` |
| Execution Detail | Historical presentation | Historical execution-related fields derived from legacy records | No proof of canonical planning or approval | `M34-D-0008` |
| Plan-versus-Actual Comparison | Trust & Evaluation analytical comparison | Comparison of a legacy projection with observed outcomes | Does not make the compared projection authoritative | `M34-D-0008` |
| Decision Memory | Historical reference composition | Historical context of legacy decision-related artifacts | No Decision Intelligence authority or immutable governance truth | `M34-D-0008` |
| Ledger Transaction | Ledger & Accounting | Ledger fact | Never proves plan, approval, authorization, intent, or actor attribution | `M34-D-0008` |

WP6 may verify only the approved negative guarantees for `SA27`-`SA30`. It
may not positively verify execution correctness, approval correctness,
authorization, human intent, decision authority, or actor attribution.

## 8. Operations-status decomposition

| Concept | Constitutional owner or binding | Meaning | Composite boundary | Decision |
| --- | --- | --- | --- | --- |
| Portfolio Status | Portfolio Intelligence | Status of portfolio-derived information | Source status, not aggregate Operations truth | `M34-D-0009` |
| Goal Status | Wealth Intelligence | Current state of Goal Target | Source status | `M34-D-0009` |
| Market Context Status | Market Intelligence | Status of market observations and context | Source status | `M34-D-0009` |
| Optimizer Status | Decision Intelligence | Optimizer lifecycle, readiness, and processing state | Operational only; no execution authority | `M34-D-0009` |
| Policy Status | Decision Intelligence | Policy evaluation and applicability | Does not become approval | `M34-D-0009` |
| Station Health | Exactly one responsible producing constitutional domain per concrete station | Operational state supplied by that domain | No platform-wide Health concept | `M34-D-0009` |
| Committee Status | Exactly one producing constitutional domain per concrete governance component | Status emitted by the component | Does not imply approval; legacy inputs remain `STOPPED_AUTHORITY` | `M34-D-0008`, `M34-D-0009` |
| Translation Status | Exactly one constitutional domain responsible for the producing translation service | Translation lifecycle state | Operational only; no investment meaning | `M34-D-0009` |
| Action Required | Experience Platform | Presentation that one or more source domains require attention | Not a decision, approval, instruction, or authorization | `M34-D-0009` |
| Operations Center Composition | No independent semantic owner; presentation composition only | Aggregated rendering of source-domain statuses | Owns none of the displayed statuses | `M34-D-0009` |

Every status preserves producing domain, `M34-D-0005` event qualifier,
timestamp, degraded-state qualifier, and provenance. Trust & Evaluation stays
independently evaluative and never owns operational state.

## 9. Instrument-analysis decomposition

| Concept | Constitutional owner | Meaning | Provenance and boundary | Decision |
| --- | --- | --- | --- | --- |
| Asset Identity | Asset Foundation | Identity of the financial instrument | Referenced by every other concept; not owned downstream | `M34-D-0010` |
| Canonical Asset Classification | Asset Foundation | Canonical classification of the instrument | Uses `M34-D-0004` | `M34-D-0004`, `M34-D-0010` |
| Market Observation | Market Intelligence | Prices, technical observations, market statistics, provider observations, and news references | Observable fact, not investment judgment | `M34-D-0010` |
| Investment Judgment | Decision Intelligence | Interpretation of observations into technical/fundamental conclusions, outlook, or expected direction | Consumes but does not own observations | `M34-D-0010` |
| Instrument-Level Derived Risk | Decision Intelligence | Risk assessment for one instrument | Distinct from Portfolio Intelligence portfolio risk | `M34-D-0010` |
| Consensus | Decision Intelligence | Aggregated judgment from one or more analytical sources | Derived judgment, not evidence or source authority | `M34-D-0010` |
| Analysis History | Decision Intelligence | Historical record of analytical outputs | Preserves context; does not prove correctness | `M34-D-0010` |
| Evaluation | Trust & Evaluation | Independent evaluation of analytical quality or correctness | Remains independent of the judgment evaluated | `M34-D-0010` |
| Instrument-Analysis Presentation | Experience Platform | Composition and rendering of independently owned concepts | Owns no business truth | `M34-D-0010` |

Every displayed field preserves semantic owner, source provenance, temporal
provenance, and applicable degraded state.

## 10. Watchlist membership mapping

| Concept | Constitutional owner | Meaning | Explicit non-implications | Decision |
| --- | --- | --- | --- | --- |
| Watchlist Membership | Experience Platform | User-maintained interaction state retaining an Asset for future viewing or investigation | No ownership, portfolio inclusion, accounting identity, recommendation, investment decision, approval, execution authorization, transaction intent, plan, policy, or human authorization | `M34-D-0011` |
| User Preference State | Experience Platform | Interaction preference expressed by Watchlist Membership | No business or investment truth | `M34-D-0011` |
| Interaction State | Experience Platform | State of the bounded user interaction | No authority over the referenced Asset or displayed analysis | `M34-D-0011` |

Transaction initiation begins only in the separately governed transaction or
execution workflow. Launching that workflow does not change membership
meaning.

## 11. Presentation and composite boundaries

| Composition | Experience responsibility | Truth retained by |
| --- | --- | --- |
| Portfolio container | Select and present one accounting scope | Ledger & Accounting plus each referenced source domain |
| Cross-portfolio surface | Compose membership, aggregate, and exposure | Ledger & Accounting and Wealth Intelligence |
| Sector presentation | Label and visualize the identified classification/grouping kind | Asset Foundation, Market Intelligence, or Portfolio Intelligence as mapped |
| Persona | Render a reference preset | Each referenced setting owner |
| Operations Center | Compose source statuses and Action Required presentation | Each producing source domain; Experience owns Action Required interaction meaning only |
| Instrument analysis | Compose identity, observations, judgments, evaluation, and history | Asset Foundation, Market Intelligence, Decision Intelligence, and Trust & Evaluation |
| Watchlist | Maintain membership interaction and render adjacent claims | Experience for membership; source domains for every displayed business claim |
| Temporal labels | Format the complete authoritative temporal tuple | Producing domain |

No composition in this table is a new domain or source of business truth.

## 12. Completeness and traceability

This artifact contains every decomposition and invariant approved by
`M34-D-0002` through `M34-D-0005` and `M34-D-0007` through `M34-D-0011`.
The audit-label mapping is `M34-D-0001` and
`M34_WP6A_DQ01_claim_family_owner_mapping.md`. Vocabulary admission is
governed by `M34-D-0006`; the current gate is `M34-D-0012`.

Context-bound owner bindings remain explicit. This artifact does not infer a
universal owner for Model Selection, Analysis Source Selection, Station
Health, Committee Status, or Translation Status, and does not treat Persona
or a presentation composition as an independently authoritative business
concept.

No Platform Architecture, Domain Constitution, frozen WP1-WP5A evidence,
implementation, runtime, M32, or M33 artifact is changed by this mapping.
WP6 remains unauthorized. M34.1 remains NO-GO.
