# M34-WP5A - Governance Decision Package

**Date:** 2026-07-19

**Status:** Complete as a neutral Architecture Review Board decision package.
Every issue and decision request remains unresolved. No owner, option,
definition, finding, disposition, or governance decision is approved here.

**Current gate:** M34-WP6 is not authorized. M34.1 remains NO-GO.

## 1. Executive Summary

M34-WP5 completed the inventory of semantic authority but could not establish
one approved owner and one governing definition for every observable product
claim. Its closed population contains 40 claim families:

- 9 `ALIGNED`;
- 19 `PROVISIONAL_MAPPING`;
- 7 `CONFLICTED`;
- 2 `STOPPED_AUTHORITY`; and
- 3 `UNKNOWN_OWNERSHIP`.

The inventory itself is complete. The governance state is not. Four blockers
prevent WP6 from using the inventory as an authority baseline:

1. the frozen WP1 audit-owner names are not explicitly mapped to the reserved
   constitutional domains;
2. several primary concepts have competing or absent owners;
3. only 7 of the 40 claim families have a directly applicable exact canonical
   Glossary definition; and
4. current execution- and decision-labelled claims must not acquire the
   canonical planning or approval authority denied by the closed M32 and M33
   decisions.

WP1 evidence rule 7 prohibits an auditor from selecting a winner when
governing artifacts conflict. WP1 stop conditions 1, 5, and 11 require the
affected work to return to the Architecture Review Board when frozen
governance conflicts, primary ownership is unresolved, or a governing
artifact would require reinterpretation. Proceeding to WP6 would force WP6 to
make those forbidden choices while evaluating correctness.

This package converts the verified WP5 escalation into twelve bounded decision
questions. It adds no repository evidence and performs no new semantic or
architecture analysis. All supporting evidence is the verified WP5 evidence
set `M34-E-0039` through `M34-E-0050` and the frozen WP2-WP4 lineage it cites.

### 1.1 Decision-package identifier boundary

The identifiers in this package are local review identifiers:

- issue: `M34-WP5A-GI-##`;
- decision question: `M34-WP5A-DQ-##`; and
- governance risk: `M34-WP5A-GR-##`.

They are not M34 register identifiers and do not allocate an `M34-D-####`.
The frozen M34 Decision Register remains empty. If the ARB decides a question,
the approved result must later receive its own canonical `M34-D-####` record
under the frozen WP1 working-artifact rules. A package-local option is never a
decision by implication.

### 1.2 Complete issue coverage

| Decision question | WP5 conflicts, candidates, and unknowns covered |
| --- | --- |
| `M34-WP5A-DQ-01` | Audit-domain namespace conflict; `AV01`; unknown approved WP1-to-constitution mapping; all 19 `PROVISIONAL_MAPPING` rows |
| `M34-WP5A-DQ-02` | Portfolio identity and strategy-container conflict; `SA01`; unknown constitutional home |
| `M34-WP5A-DQ-03` | Cross-portfolio exposure conflict; `SA02`; `AV02` |
| `M34-WP5A-DQ-04` | Sector-classification authority conflict; `SA11`; `AV03` |
| `M34-WP5A-DQ-05` | Temporal/failure vocabulary conflict; `SA16`; `AV04` |
| `M34-WP5A-DQ-06` | Canonical-vocabulary coverage; `AV05`, `AV06`, `AV12`; all 33 claim families without an exact applicable Glossary definition |
| `M34-WP5A-DQ-07` | Goal, persona, policy, limit, and configuration conflicts; `SA25`, `SA39`; `AV11`; corresponding unknown boundary |
| `M34-WP5A-DQ-08` | Legacy execution/decision authority; `SA27`, `SA28`, `SA29`, `SA30`; `AV07`, `AV08`, `AV09`; stopped-authority unknown |
| `M34-WP5A-DQ-09` | Operations composite ownership; `SA36`; `AV10`; unknown status grammar and owner |
| `M34-WP5A-DQ-10` | Instrument-analysis ownership; `SA21`; instrument-analysis portion of `AV13` |
| `M34-WP5A-DQ-11` | Watchlist-membership ownership; `SA38`; Watchlist portion of `AV13` |
| `M34-WP5A-DQ-12` | ARB escalation result and bounded WP6 entry set; all 31 non-`ALIGNED` claim families |

No WP5 conflict group, authority-violation candidate, or unknown-ownership
category is omitted. Overlap is retained where one claim needs both an owner
ruling and a vocabulary ruling.

## 2. Decision Register

This is a register of questions presented to the ARB, not the canonical M34
Decision Register. Every entry has status `PENDING_ARB`. Options are neutral
alternatives; their presence does not imply endorsement or equal
constitutional cost.

### M34-WP5A-DQ-01 - Govern the M34 audit-domain namespace

- Issue identifier: `M34-WP5A-GI-01`
- Status: `PENDING_ARB`
- Affected claim families: `SA08`, `SA09`, `SA10`, `SA12`, `SA13`, `SA15`,
  `SA18`, `SA19`, `SA20`, `SA22`, `SA23`, `SA26`, `SA30`, `SA31`, `SA32`,
  `SA33`, `SA34`, `SA35`, `SA37`
- Affected domains: Portfolio Intelligence, Decision Intelligence, Trust &
  Evaluation; the WP1 audit categories Analytics, Portfolio Intelligence,
  and AI Evaluation

#### Background

WP1 names audit corpus/owner categories `ANALYTICS`,
`PORTFOLIO_INTELLIGENCE`, and `AI_EVALUATION`. The Platform Constitution
reserves the different domain names Portfolio Intelligence, Decision
Intelligence, and Trust & Evaluation. WP5 found plausible responsibility
mappings but no approved authority that makes those names aliases. In
particular, the WP1 phrase Portfolio Intelligence can refer to two different
constitutional domains depending on the claim.

#### Evidence

`M34-E-0039`, `M34-E-0040`, `M34-E-0043`, `M34-E-0044`, `M34-E-0045`,
`M34-E-0048`, `M34-E-0049`, `M34-E-0050`; WP5 sections 2, 4, 5, and 11.

#### Governing rules

- Platform Architecture sections 6 and 12, especially V1 and V3;
- Platform Architecture section 11, especially G2, G3, G4, and G6;
- WP1 sections 1.4 and 1.5; and
- WP1 stop conditions 1, 5, and 11.

#### Affected documents and artifacts

Platform Architecture section 6; WP1 sections 1.5 and 2.4/2.7/2.8; WP5
sections 2-5; the future ARB result in the M34 Decision Register; any future
M34 report that assigns a semantic owner. Frozen artifacts remain unchanged
unless a separately authorized governance process says otherwise.

#### Available options and consequences

| Option | Neutral description | Consequences |
| --- | --- | --- |
| A | Approve an explicit context-sensitive mapping from every WP1 audit label to one constitutional owner for each claim family | Preserves WP1 labels as audit categories; requires a complete mapping table and prohibits treating one label as a universal domain alias |
| B | Require a versioned WP1 governance addendum or superseding protocol before any mapping is used | Makes the mapping part of the M34 audit authority; keeps WP6 blocked until that new artifact is approved and traceably linked |
| C | Require post-ARB M34 work to use only reserved constitutional domain names, while frozen WP1/WP2-WP5 labels remain historical | Avoids future alias use; requires an explicit interpretation rule for references back to frozen artifacts |
| D | Approve no mapping and exclude every affected provisional family from the WP6 entry set | Avoids reinterpretation; materially narrows WP6 and must remain visible in the eventual M34 readiness result |
| E | Amend a reserved constitutional domain name or boundary | Requires the Platform Architecture amendment process and Decision Log synchronization; cannot take effect through M34 alone |

#### Current consequence

Nineteen claim families cannot be treated as owner-verified. Full WP6 remains
blocked.

#### Risks

Implicit aliasing would violate one-term/one-meaning and could assign the same
claim to different domains in different work packages. A broad mapping could
also hide real concept-level conflicts.

#### Dependencies and downstream impact

This decision precedes `M34-WP5A-DQ-02` through `M34-WP5A-DQ-11` whenever
those decisions use WP1 labels, and it precedes `M34-WP5A-DQ-12`. It affects
the owner column and review authority for WP6, later M34 traceability, and any
M35+ document that cites M34 audit-domain names. It does not change existing
implementation or runtime behavior.

#### Required ARB decision

Select one option, state whether it is an interpretation, a new M34 governance
artifact, or a constitutional amendment, and provide an exhaustive mapping or
exclusion set. No implicit or partial alias is sufficient.

### M34-WP5A-DQ-02 - Establish authority for portfolio identity and the strategy container

- Issue identifier: `M34-WP5A-GI-02`
- Status: `PENDING_ARB`
- Affected claim families: `SA01`
- Affected domains: Ledger & Accounting, Portfolio Intelligence, Decision
  Intelligence, Wealth Intelligence, Experience Platform; the WP1 Portfolio
  audit category

#### Background

The portfolio domain model defines Portfolio as a strategy and accounting
scope, while the Platform Constitution distributes the facts and meanings
rendered inside that scope across several domains. The constitution does not
explicitly name a domain that owns the portfolio identifier/container itself.
Experience owns selection interaction only, not portfolio truth.

#### Evidence

`M34-E-0041`, `M34-E-0043`, `M34-E-0044`, `M34-E-0048`, `M34-E-0049`;
WP5 `SA01`, sections 5 and 9.

#### Governing rules

- Platform Architecture sections 6, 7.1, and 11 G3-G4;
- Platform Architecture section 6.9, Experience owns rendering and no truth;
- WP1 section 1.5 one-concept/one-owner rule; and
- WP1 stop condition 5.

#### Affected documents and artifacts

Platform Architecture section 6; `PORTFOLIO_DOMAIN_MODEL.md`; WP1 Portfolio
owner rule; WP3 selected-portfolio scope classifications; WP4
`listPortfolios` lineage; WP5 `SA01`; future Glossary entry if the term is
governed as a platform noun.

#### Available options and consequences

| Option | Neutral description | Consequences |
| --- | --- | --- |
| A | Assign the portfolio identity/container concept to one existing constitutional domain selected by the ARB | Closes the owner gap if the domain boundary already permits it; may require a lower-level ADR or, if the boundary changes, constitutional amendment |
| B | Decompose `SA01` into separately owned identity, accounting-scope, strategy-metadata, goal, and selection concepts | Preserves one owner per smaller concept; requires WP6 entry to reference the approved decomposition rather than treating `SA01` as one owner |
| C | Treat Portfolio only as an M34 scope label and exclude container identity/strategy meaning from WP6 | Avoids an owner appointment; leaves a material product claim outside the correctness audit and must constrain M34 readiness |
| D | Determine that existing authority is insufficient and return the question for a higher-level amendment | Keeps the issue unresolved until the constitutional process completes |

#### Current consequence

The selected-portfolio identifier, name, goal target, and container meaning
cannot share one assumed owner in WP6.

#### Risks

A container may become a hidden domain by accumulation. Conversely, splitting
it without an explicit scope contract may erase the invariant that all
portfolio facts refer to the same accounting boundary.

#### Dependencies and downstream impact

Depends on `M34-WP5A-DQ-01` if WP1 labels remain operative. It constrains
`M34-WP5A-DQ-03`, `M34-WP5A-DQ-07`, and `M34-WP5A-DQ-12`. It affects future
semantic reviews of selected scope but not current storage, APIs, or runtime.

#### Required ARB decision

Approve one existing-domain owner, an explicit decomposition, an explicit
exclusion, or escalation to constitutional amendment. The decision must say
what Portfolio identity means without creating a new domain.

### M34-WP5A-DQ-03 - Govern cross-portfolio exposure

- Issue identifier: `M34-WP5A-GI-03`
- Status: `PENDING_ARB`
- Affected claim families: `SA02`
- Affected domains: Wealth Intelligence, Portfolio Intelligence, Ledger &
  Accounting, Market Intelligence, Experience Platform

#### Background

The root surface combines holdings and prices across portfolios and presents
symbol exposure and portfolio membership. The Portfolio domain model assigns
overall cross-boundary exposure to Wealth, while the current composition is
entered through the existing portfolio product experience. Route placement
cannot decide semantic authority.

#### Evidence

`M34-E-0041`, `M34-E-0043`, `M34-E-0048`, `M34-E-0049`; WP3 root-surface
inventory; WP4 holdings/prices lineage; WP5 `SA02` and `AV02`.

#### Governing rules

- Platform Architecture sections 6.5, 6.8, 6.9, and 7.1;
- `PORTFOLIO_DOMAIN_MODEL.md` sections 7 and 10;
- WP1 section 1.5; and
- WP1 stop condition 5.

#### Affected documents and artifacts

Platform Architecture Wealth/Portfolio responsibilities;
`PORTFOLIO_DOMAIN_MODEL.md`; WP3 `/` inventory; WP4 holdings/prices shared
contracts; WP5 `SA02`; future canonical vocabulary for cross-portfolio
exposure.

#### Available options and consequences

| Option | Neutral description | Consequences |
| --- | --- | --- |
| A | Govern the claim as Wealth Intelligence exposure derived from portfolio, ledger, market, and classification inputs | Aligns cross-portfolio meaning with the current constitutional Wealth boundary; does not require moving the current route |
| B | Govern the claim as a narrowly defined portfolio-collection projection distinct from Wealth exposure, assigned to an existing domain | Requires a precise definition proving it is not the Wealth concept and a canonical name that avoids duplicate meaning |
| C | Decompose portfolio membership from cross-portfolio exposure and assign each concept independently | Preserves separate identity/scope and derived-measure ownership; increases the number of explicit WP6 claim records |
| D | Exclude the cross-portfolio claim from WP6 | Leaves the root surface outside semantic-correctness readiness and must be reflected in the M34 result |

#### Current consequence

WP6 cannot judge the root surface's combined exposure against an assumed
Portfolio owner.

#### Risks

An unqualified decision could duplicate Wealth semantics or let Experience
own a cross-domain calculation by composition.

#### Dependencies and downstream impact

Depends on `M34-WP5A-DQ-02` for Portfolio scope language and on
`M34-WP5A-DQ-06` for canonical terminology. Precedes
`M34-WP5A-DQ-12`. No implementation or route change follows automatically.

#### Required ARB decision

Choose the governing concept boundary and one existing owner, or explicitly
exclude the claim. State whether route/navigation placement is irrelevant to
the ownership ruling.

### M34-WP5A-DQ-04 - Govern sector classification and copied sector values

- Issue identifier: `M34-WP5A-GI-04`
- Status: `PENDING_ARB`
- Affected claim families: `SA11`; dependent portions of `SA10`, `SA19`,
  `SA22`, `SA23`, and `SA39`
- Affected domains: Asset Foundation, Market Intelligence, Portfolio
  Intelligence, Ledger & Accounting, Experience Platform

#### Background

The constitution assigns canonical classification to Asset Foundation and
treats Market Intelligence/provider metadata as evidence. Current read
lineage also carries sector values through Portfolio and Watchlist
persistence. WP5 did not determine which displayed value is canonical, copied,
cached, or unresolved.

#### Evidence

`M34-E-0039`, `M34-E-0042`, `M34-E-0043`, `M34-E-0048`, `M34-E-0049`; WP4
persistence/lineage inventory; WP5 `SA11` and `AV03`.

#### Governing rules

- Platform Architecture sections 6.1, 6.2, 7.4, 11 G2/G4/G6, and 12 V1;
- Market Data Platform sections cited by `M34-E-0042`;
- WP1 evidence rules 5 and 7; and
- WP1 one-concept/one-owner rule.

#### Affected documents and artifacts

Platform Architecture Asset/Market boundaries; `MARKET_DATA_PLATFORM.md`;
Portfolio and Watchlist domain/read documentation; WP3 affected surfaces;
WP4 sector-bearing contracts and persistence sources; WP5 `SA11`.

#### Available options and consequences

| Option | Neutral description | Consequences |
| --- | --- | --- |
| A | Confirm Asset Foundation as canonical owner and classify all other sector fields as identified projections or evidence | Requires WP6 to verify projection identity/provenance against that authority; no storage change is implied by the ruling |
| B | Approve a bounded distinction between canonical asset classification and context-specific analytical grouping | Requires separate canonical terms and owners; prevents the two concepts from sharing the unqualified word `sector` |
| C | Treat current displayed sector as non-canonical/unknown until an authoritative relationship is established | Allows fail-closed semantic review but prevents a positive correctness conclusion for dependent claims |
| D | Exclude sector-dependent claims from WP6 | Narrows allocation, factor, contribution, attribution, and limits coverage |

#### Current consequence

Sector-labelled output cannot be used as an authority premise for dependent
WP6 checks.

#### Risks

Treating a copied value as authority can create two classification truths.
Treating analytical grouping as canonical classification can leak a consumer
taxonomy into Asset Foundation.

#### Dependencies and downstream impact

`M34-WP5A-DQ-06` must register or classify any distinct terminology approved
here. This decision precedes WP6 review of sector allocation, factor,
contribution, attribution, and sector-limit claims. It changes no current row
or runtime source.

#### Required ARB decision

Approve the authority/projection distinction, approve a bounded two-concept
distinction, classify the current claim as unknown, or exclude it.

### M34-WP5A-DQ-05 - Govern temporal and degraded-state vocabulary

- Issue identifier: `M34-WP5A-GI-05`
- Status: `PENDING_ARB`
- Affected claim families: `SA07`, `SA16`, `SA17`, `SA36`, `SA37`; temporal
  dimensions of all other time-bearing claims
- Affected domains: every producing source domain and Experience Platform

#### Background

WP5 identified several different events behind the words `Updated`, `as of`,
`current`, and `fresh`: source observation, retrieval, calculation, analysis,
snapshot, batch evaluation, and client refresh completion. The producing
domain owns the event and its degraded meaning; Experience renders the label
and supplied state.

#### Evidence

`M34-E-0042`, `M34-E-0045`, `M34-E-0047`, `M34-E-0048`, `M34-E-0049`; WP3
timestamp claims; WP4 lineage unknowns `L02`, `L10`, and `L14`; WP5 `SA16`
and `AV04`.

#### Governing rules

- Platform Architecture goals and section 8 explainability, provenance, and
  loud failure;
- Platform Architecture sections 6.2 and 6.9;
- Platform Architecture section 12 V1-V2; and
- WP1 ownership rule for degraded-state meaning versus rendering.

#### Affected documents and artifacts

Platform Architecture cross-cutting principles; `MARKET_DATA_PLATFORM.md`;
domain documents for time-bearing calculations/records; Glossary; WP3
surface labels; WP4 transports and transformations; WP5 `SA16`.

#### Available options and consequences

| Option | Neutral description | Consequences |
| --- | --- | --- |
| A | Require a distinct canonical term and owning domain for each material event time | Maximizes semantic precision; WP6 must verify each label against its exact event and degraded-state contract |
| B | Approve a shared qualified temporal grammar with mandatory event/source qualifiers | Allows a common presentation pattern while preserving source-domain ownership; unqualified uses remain outside positive verification |
| C | Permit selected existing labels as ordinary-language presentation only when a separate authoritative time label is also present | Requires the ARB to identify the non-normative labels and the authoritative companion fields |
| D | Exclude time/freshness-dependent claims from WP6 | Prevents WP6 from establishing failure transparency or trust readiness for those claims |

#### Current consequence

WP6 cannot decide whether a displayed timestamp or degraded state truthfully
answers “Can I trust the displayed values?”

#### Risks

One word may silently collapse multiple clocks. Experience may accidentally
become the owner of freshness by timing a request rather than rendering the
source domain's status.

#### Dependencies and downstream impact

Depends on source-domain rulings where ownership is unresolved and on
`M34-WP5A-DQ-06` for vocabulary. It constrains the WP6 failure-transparency
entry set and `M34-WP5A-DQ-12`. No runtime freshness behavior is evaluated or
changed.

#### Required ARB decision

Approve one temporal naming policy, identify its authority boundary, and state
which time-bearing claim families are eligible for WP6.

### M34-WP5A-DQ-06 - Govern canonical-vocabulary coverage for WP6

- Issue identifier: `M34-WP5A-GI-06`
- Status: `PENDING_ARB`
- Affected claim families: `SA01`, `SA02`, `SA03`, `SA04`, `SA06`, `SA07`,
  `SA08`, `SA09`, `SA10`, `SA11`, `SA12`, `SA13`, `SA14`, `SA15`, `SA16`,
  `SA18`, `SA19`, `SA20`, `SA21`, `SA22`, `SA23`, `SA24`, `SA25`, `SA27`,
  `SA28`, `SA29`, `SA30`, `SA35`, `SA36`, `SA37`, `SA38`, `SA39`, `SA40`
- Affected domains: all constitutional domains represented by those claims;
  Experience Platform as consumer; governance owner of the canonical Glossary

#### Background

The Platform Constitution declares the Glossary the only canonical vocabulary
and requires platform nouns to be registered before reliance. WP5 found exact
applicable Glossary coverage for only 7 of 40 claim families. Missing terms
include common user-facing nouns and narrower terms of art. WP5 did not decide
which words are platform nouns, which are ordinary language, which need
qualification, or which claims must be excluded until registered.

#### Evidence

`M34-E-0039`, `M34-E-0047`, `M34-E-0048`, `M34-E-0049`, `M34-E-0050`; WP5
sections 3, 6, 8, and 9.

#### Governing rules

- Platform Architecture section 12 V1-V4;
- Platform Architecture section 11 G2-G5;
- WP1 canonical-vocabulary owner rule and evidence rule 7; and
- WP1 stop condition 11.

#### Affected documents and artifacts

`docs/GLOSSARY.md`; every domain constitution/design that currently defines
or uses an affected term; System Guide and other explanatory documentation;
WP1 owner vocabulary; WP3 labels; WP5 shared terminology inventory; future
WP6 semantic test basis.

#### Available options and consequences

| Option | Neutral description | Consequences |
| --- | --- | --- |
| A | Require exact Glossary entries for all 33 uncovered claim families before any enters WP6 | Maximizes canonical coverage; WP6 remains blocked until owners approve every required term and governance synchronization is complete |
| B | Approve a bounded WP6 subset and require Glossary coverage only for terms used by that subset | Allows partial WP6; every excluded term/claim remains a visible readiness limitation |
| C | Classify an explicit list as ordinary language rather than platform terms, and register only the remaining terms of art | Reduces vocabulary work; requires precise criteria so ordinary words cannot carry hidden business meaning |
| D | Approve temporary reliance on lower-level domain definitions | Conflicts with V1-V2 unless accompanied by a constitutional amendment or an explicit ruling that the words are not platform nouns; cannot be treated as ordinary M34 synchronization |
| E | Keep WP6 blocked and return terminology to the owning domains without setting a readiness subset | Preserves governance purity; M34 cannot advance until later approved vocabulary work completes |

#### Current consequence

Most claim families lack the single canonical definition against which WP6
could judge semantic correctness.

#### Risks

Registering terms before ownership decisions can canonize the wrong boundary.
Registering every display label can overload the Glossary. Registering too
little permits private dialects and duplicate meanings.

#### Dependencies and downstream impact

Must follow the owner/boundary decisions in `M34-WP5A-DQ-01` through
`M34-WP5A-DQ-05` and `M34-WP5A-DQ-07` through `M34-WP5A-DQ-11` for every term
they affect. It directly controls `M34-WP5A-DQ-12`. Approved vocabulary work,
if any, is a later governance action and not performed by WP5A.

#### Required ARB decision

Approve the exact vocabulary entry set or exact WP6 subset, classify any
ordinary-language exceptions, identify the owning domain for every new term,
and state whether any higher-level amendment is required.

### M34-WP5A-DQ-07 - Govern goals, persona, policy, limits, and configuration

- Issue identifier: `M34-WP5A-GI-07`
- Status: `PENDING_ARB`
- Affected claim families: `SA25`, `SA39`
- Affected domains: Decision Intelligence, Wealth Intelligence, Portfolio
  Intelligence, Asset Foundation, Market Intelligence, Experience Platform;
  the WP1 Portfolio and Portfolio Intelligence audit categories

#### Background

Current surfaces group portfolio goal profiles, persona, optimizer policy,
portfolio/sector limits, model selection, source selection, fallback, and
other configuration. Storage or route grouping does not create one semantic
owner. The constitution assigns life-level goals to Wealth Intelligence,
policy envelopes to Decision Intelligence, and underlying source/classification
semantics to their respective domains.

#### Evidence

`M34-E-0039`, `M34-E-0042`, `M34-E-0043`, `M34-E-0044`, `M34-E-0047`,
`M34-E-0048`, `M34-E-0049`; WP3 Goal Wizard/Settings/Optimizer/Operations
inventory; WP4 configuration contracts; WP5 `SA25`, `SA39`, and `AV11`.

#### Governing rules

- Platform Architecture sections 6.5, 6.6, 6.8, 6.9, and 7.2 configuration
  gate;
- Platform Architecture sections 11-12;
- WP1 one-concept/one-owner rule; and
- WP1 stop condition 5.

#### Affected documents and artifacts

Platform Architecture domain responsibilities; `PORTFOLIO_DOMAIN_MODEL.md`;
`OPTIMIZER_PHILOSOPHY.md`; Market/Asset authority documents; WP3 affected
surfaces; WP4 settings/persona/profile contracts; WP5 `SA25` and `SA39`;
Glossary.

#### Available options and consequences

| Option | Neutral description | Consequences |
| --- | --- | --- |
| A | Decompose the grouped claims and assign each setting family to the existing domain whose future behavior it governs | Preserves one owner per rule; requires an exhaustive family map before WP6 |
| B | Approve one existing domain as owner of a precisely bounded composite policy object while all source settings remain references | Requires proof that the composite is a new owned meaning rather than a container that absorbs other domains' rules |
| C | Separate portfolio strategy metadata from Wealth goals and Decision policy, with each retaining its current governing source | Requires distinct canonical terms and explicit conversion/reference rules |
| D | Exclude unresolved goal/configuration claims from WP6 | Allows other claims to proceed but prevents a full product-readiness conclusion for affected surfaces |

#### Current consequence

WP6 cannot treat the Settings page, goal profile, portfolio persona, or policy
summary as one authoritative concept.

#### Risks

A settings store or form can become a false business domain. A broad “policy”
term can mix human intent, decision constraints, data-source configuration,
and portfolio analytics limits.

#### Dependencies and downstream impact

Depends on `M34-WP5A-DQ-01` and `M34-WP5A-DQ-02`; feeds
`M34-WP5A-DQ-06` and `M34-WP5A-DQ-12`. The ruling governs future semantic
review only; it does not authorize configuration, schema, or runtime changes.

#### Required ARB decision

Approve an exhaustive existing-domain decomposition, a bounded composite
concept, an explicit distinction, or an exclusion set. No new Configuration,
Goal, or Portfolio Workspace domain may be created by this ruling.

### M34-WP5A-DQ-08 - Constrain legacy execution and decision terminology

- Issue identifier: `M34-WP5A-GI-08`
- Status: `PENDING_ARB`
- Affected claim families: `SA27`, `SA28`, `SA29`, `SA30`
- Affected domains: Decision Intelligence, Trust & Evaluation, Ledger &
  Accounting, Experience Platform; M32/M33 governance boundary

#### Background

Existing surfaces display an execution-plan projection, legacy decision
records, execution detail, plan-versus-actual comparisons, and decision
memory. M32 closed canonical execution planning as NO-GO. M33 ended
`STOP_M33_RUNTIME` and denied approval authority and actor attribution to
legacy rows. WP5 may inventory these reads but cannot authorize the meanings
their unqualified labels might imply.

#### Evidence

`M34-E-0044`, `M34-E-0045`, `M34-E-0046`, `M34-E-0047`, `M34-E-0048`,
`M34-E-0049`, `M34-E-0050`; WP5 `SA27`, `SA28`, `SA29`, `SA30`, `AV07`,
`AV08`, and `AV09`.

#### Governing rules

- M32 Epic Closeout final readiness and active legacy-path decision;
- M33.11 `STOP_M33_RUNTIME` decision and non-adoption effects;
- Platform Architecture sections 6.3, 6.6, 6.7, 7.2, and 8 human sovereignty;
- Platform Architecture section 11 G2/G4/G6; and
- WP1 exclusions and stop condition 7.

#### Affected documents and artifacts

`M32_EPIC_CLOSEOUT.md`; `M33_11_supabase_auth_security_state_and_assurance_proof_of_concept.md`;
M32/M33 Decision Log entries; `OPTIMIZER_PHILOSOPHY.md`;
`EXECUTION_INTELLIGENCE_UX.md`; WP3 optimizer/evaluation surfaces; WP4 legacy
decision/execution read contracts; WP5 `SA27`-`SA30`; Glossary.

#### Available options and consequences

| Option | Neutral description | Consequences |
| --- | --- | --- |
| A | Approve precise non-authoritative definitions for each legacy read while preserving canonical-planning NO-GO and `STOP_M33_RUNTIME` | Allows semantic review of historical/display claims only; the ruling must state what each record does not prove |
| B | Require distinct qualified terminology before the claims enter WP6 | Avoids authority overclaim; keeps the affected claims blocked until later vocabulary governance completes |
| C | Exclude all four claim families and their dependent trust/evaluation claims from WP6 | Preserves closed boundaries; materially narrows evaluation coverage and later readiness |
| D | Keep the records in inventory as `STOPPED_AUTHORITY` and permit only negative verification that they do not establish plan/approval authority | Allows WP6 to test the prohibition, not positive execution or approval correctness |

An option that grants canonical execution-plan, human-approval, identity, or
runtime authority is outside this package and cannot be selected without a
separate reopen process satisfying the predecessor criteria.

#### Current consequence

WP6 cannot use these records as authoritative plans, approvals, execution
facts, or actor-attributed decisions.

#### Risks

Terminology drift could reopen M32/M33 by implication. Evaluation language
could also make a linked transaction prove a plan or approval that the record
does not possess.

#### Dependencies and downstream impact

The M32/M33 boundary is an immutable input, not a dependency to be revisited.
This question can be reviewed in parallel with owner questions but must
precede `M34-WP5A-DQ-06` for legacy terms and `M34-WP5A-DQ-12`. No option
authorizes runtime work.

#### Required ARB decision

Approve one bounded treatment that explicitly preserves both predecessor
decisions and identifies the exact positive or negative WP6 scope.

### M34-WP5A-DQ-09 - Govern composite operations-status claims

- Issue identifier: `M34-WP5A-GI-09`
- Status: `PENDING_ARB`
- Affected claim families: `SA36`; related trust-summary portion of `SA37`
- Affected domains: Portfolio Intelligence, Decision Intelligence, Trust &
  Evaluation, Market Intelligence, Ledger & Accounting, Experience Platform

#### Background

Operations Center composes portfolio summary, goal, market context, optimizer,
committee, policy, station-health, trust, translation, and action-required
states. No constitution grants a composition service or route ownership of
all those source meanings. WP5 could not determine whether each status is a
source-domain fact, a separately derived concept, or presentation language.

#### Evidence

`M34-E-0039`, `M34-E-0042`, `M34-E-0043`, `M34-E-0044`, `M34-E-0045`,
`M34-E-0047`, `M34-E-0048`, `M34-E-0049`; WP3 Operations Center inventory;
WP4 operations-status lineage; WP5 `SA36`, `SA37`, and `AV10`.

#### Governing rules

- Platform Architecture sections 6.2, 6.5-6.7, 6.9, 7.1, and 8;
- Experience owns rendering and no truth;
- one concept/one owner and downward-only dependency law; and
- WP1 stop condition 5.

#### Affected documents and artifacts

Platform Architecture affected domain boundaries; Operations Center
documentation; WP3 `/operations-center`; WP4 operations-status/trust-report
contracts; WP5 `SA36`-`SA37`; Glossary.

#### Available options and consequences

| Option | Neutral description | Consequences |
| --- | --- | --- |
| A | Decompose the response into source-domain statuses and make the composite explicitly presentation-only | Preserves source ownership; WP6 must verify each subclaim independently and cannot judge one aggregate “health” truth |
| B | Approve a precisely defined derived operations-status concept owned by one existing domain, with source statuses retained as inputs | Requires a new canonical concept and proof that the dependency direction and Trust independence remain constitutional |
| C | Classify selected labels as Experience interaction/navigation state with no business-truth meaning | Those labels cannot support trust, correctness, or action claims in WP6 |
| D | Exclude the composite status family from WP6 | Prevents a correctness conclusion for Operations Center and related trust summary |

#### Current consequence

WP6 cannot select one owner or definition for station health, committee
status, or action-required state.

#### Risks

Composition may transfer authority upward, make Trust operational, or let
Experience invent a status. A single health label may conceal conflicting
source-domain failures.

#### Dependencies and downstream impact

Depends on `M34-WP5A-DQ-01`; interacts with `M34-WP5A-DQ-05` for status time
and degraded meaning, `M34-WP5A-DQ-06` for terms, and
`M34-WP5A-DQ-08` where legacy decision state is an input. Precedes
`M34-WP5A-DQ-12`.

#### Required ARB decision

Approve a source-status decomposition, an existing-domain derived concept, an
Experience-only classification, or an exclusion set, with explicit Trust and
failure-transparency constraints.

### M34-WP5A-DQ-10 - Govern the instrument-analysis product contract

- Issue identifier: `M34-WP5A-GI-10`
- Status: `PENDING_ARB`
- Affected claim families: `SA20`, `SA21`; instrument-analysis dependencies in
  `SA03`, `SA07`, and `SA38`
- Affected domains: Market Intelligence, Decision Intelligence, Portfolio
  Intelligence, Trust & Evaluation, Asset Foundation, Experience Platform

#### Background

Stock and Watchlist surfaces group technical, fundamental, news, signal,
upside, risk, consensus, history, source, and freshness claims. The
constitutional model separates observations, beliefs, portfolio-derived risk,
evaluation, identity, and presentation. No governing artifact establishes
one owner for the grouped instrument-analysis contract.

#### Evidence

`M34-E-0039`, `M34-E-0042`, `M34-E-0043`, `M34-E-0044`, `M34-E-0047`,
`M34-E-0048`, `M34-E-0049`; WP3 stock/watchlist claims; WP4 stock/watchlist
lineage; WP5 `SA20`, `SA21`, and `AV13`.

#### Governing rules

- Platform Architecture sections 6.1, 6.2, 6.5-6.7, 6.9, 7.1, 7.4, and 12;
- facts-versus-judgment boundary;
- Experience owns rendering and no truth; and
- WP1 stop condition 5.

#### Affected documents and artifacts

Platform Architecture domain responsibilities; Market Data and optimizer
authority documents; current architecture instrument-analysis descriptions;
WP3 `/stock/[symbol]` and `/watchlist`; WP4 corresponding read contracts;
WP5 `SA20`-`SA21`; Glossary.

#### Available options and consequences

| Option | Neutral description | Consequences |
| --- | --- | --- |
| A | Decompose the grouped contract into observation, belief, derived-risk, evaluation, identity, and presentation concepts with separate existing owners | Preserves constitutional boundaries; requires field-level WP6 records and explicit provenance between concepts |
| B | Approve one existing domain as owner of a narrowly defined instrument-analysis judgment while other fields remain source-domain references | Requires a precise contract boundary and canonical term; cannot absorb prices, identity, portfolio risk, or evaluation truth |
| C | Approve only a bounded subset for WP6 and classify the remaining fields as unknown ownership | Allows partial review; omitted instrument claims remain blockers or explicit limitations |
| D | Exclude the grouped instrument-analysis claim from WP6 | Avoids an unsupported owner ruling; leaves Stock/Watchlist investigation readiness unresolved |

#### Current consequence

WP6 cannot judge the grouped Stock/Watchlist analysis output as one owned
semantic contract.

#### Risks

An AI/analysis label may collapse evidence and judgment. An instrument risk
score may be confused with portfolio risk. Source lists may appear to prove
the correctness of derived judgments.

#### Dependencies and downstream impact

Depends on `M34-WP5A-DQ-01` for the WP1 Portfolio Intelligence label and on
`M34-WP5A-DQ-04` for classification inputs. Feeds
`M34-WP5A-DQ-05`, `M34-WP5A-DQ-06`, `M34-WP5A-DQ-11`, and
`M34-WP5A-DQ-12`.

#### Required ARB decision

Approve an explicit decomposition, a bounded existing-domain concept, a
partial entry set, or exclusion. The ruling must distinguish evidence,
judgment, evaluation, and presentation.

### M34-WP5A-DQ-11 - Govern Watchlist membership

- Issue identifier: `M34-WP5A-GI-11`
- Status: `PENDING_ARB`
- Affected claim families: `SA38`; Watchlist-scoped portion of `SA21`
- Affected domains: Experience Platform, Decision Intelligence, Market
  Intelligence, Asset Foundation; any existing domain proposed by the ARB

#### Background

Watchlist membership is user-maintained product state. The current surface
also consumes Market and instrument-analysis claims and can initiate a
portfolio transaction, but none of those dependencies necessarily owns the
membership concept. Experience may capture human intent, yet it owns no
portfolio truth. No governing artifact appoints an owner.

#### Evidence

`M34-E-0039`, `M34-E-0042`, `M34-E-0044`, `M34-E-0047`, `M34-E-0048`,
`M34-E-0049`; WP3 Watchlist inventory; WP4 Watchlist lineage; WP5 `SA38` and
`AV13`.

#### Governing rules

- Platform Architecture sections 6.1, 6.2, 6.6, 6.9, 7.1, and 12;
- Experience writes only expressions of human intent routed to the owner;
- one concept/one owner; and
- WP1 stop condition 5.

#### Affected documents and artifacts

Platform Architecture affected boundaries; Watchlist implementation
documentation; WP3 `/watchlist`; WP4 Watchlist contract/persistence lineage;
WP5 `SA38`; Glossary.

#### Available options and consequences

| Option | Neutral description | Consequences |
| --- | --- | --- |
| A | Assign membership to Experience Platform as interaction/preference vocabulary only | Requires a ruling that membership carries no financial-truth, recommendation, or portfolio-authority meaning |
| B | Assign membership to Decision Intelligence as recorded human interest or investigation intent | Requires a canonical intent definition and separation from recommendation and decision records |
| C | Assign membership to another existing domain with an explicit boundary rationale | May require an ADR or constitutional amendment depending on whether the chosen boundary already permits the concept |
| D | Exclude membership semantics from WP6 while retaining dependent observations as separately owned claims | Allows analysis of data shown on the route but not the meaning or correctness of membership itself |

#### Current consequence

WP6 cannot verify whether adding, removing, or displaying a Watchlist item has
the intended product meaning.

#### Risks

A convenience feature may become an ownerless source of decision intent, or
Experience may gain business truth through state capture. Conversely, placing
it in Decision Intelligence may overstate a lightweight preference.

#### Dependencies and downstream impact

Depends on `M34-WP5A-DQ-10` if instrument-analysis meaning is part of the
membership contract, and feeds `M34-WP5A-DQ-06` and
`M34-WP5A-DQ-12`. It authorizes no model, route, or runtime change.

#### Required ARB decision

Assign the concept to one existing domain with a bounded meaning, or exclude
it. State explicitly what membership does not imply.

### M34-WP5A-DQ-12 - Decide the WP6 entry set after governance resolution

- Issue identifier: `M34-WP5A-GI-12`
- Status: `PENDING_ARB`
- Affected claim families: `SA01`, `SA02`, `SA08`, `SA09`, `SA10`, `SA11`,
  `SA12`, `SA13`, `SA15`, `SA16`, `SA18`, `SA19`, `SA20`, `SA21`, `SA22`,
  `SA23`, `SA25`, `SA26`, `SA27`, `SA28`, `SA29`, `SA30`, `SA31`, `SA32`,
  `SA33`, `SA34`, `SA35`, `SA36`, `SA37`, `SA38`, `SA39`
- Affected domains: all domains selected or referenced by
  `M34-WP5A-DQ-01` through `M34-WP5A-DQ-11`

#### Background

WP5 is complete but returned the WP6 handoff. After the substantive decisions
above, the ARB must decide whether the resulting authority baseline supports
full WP6, a precisely bounded WP6 subset, or continued NO-GO. This question
does not redefine WP6 or decide M34's terminal outcome.

#### Evidence

`M34-E-0048`, `M34-E-0049`, `M34-E-0050`; `M34-R-0014`, `M34-R-0015`; all
approved results, if any, from `M34-WP5A-DQ-01` through
`M34-WP5A-DQ-11`.

#### Governing rules

- WP1 evidence rules, ownership model, review process, and stop conditions;
- frozen M34 exit choices and M34.1 gate;
- Platform Architecture sections 11-12; and
- the unchanged M32/M33 decisions.

#### Affected documents and artifacts

Future M34 Decision Register and Review Log records; future WP6 report scope;
M34 checkpoint/readiness records; roadmap and Decision Log only at their
separately authorized synchronization point. WP1-WP5 remain frozen historical
inputs.

#### Available options and consequences

| Option | Neutral description | Consequences |
| --- | --- | --- |
| A | Authorize full WP6 after every entry condition in section 8 is met for all 40 families | Preserves complete audit coverage; requires every included owner/definition conflict to be closed first |
| B | Authorize a bounded WP6 subset with a complete included/excluded family list and explicit readiness effects | Allows progress without hidden inference; excluded claims cannot support `READY_FOR_PORTFOLIO_HOME_SLICE` unless the ARB separately states why their omission is non-material |
| C | Keep WP6 NO-GO pending revision or completion of one or more governance decisions | Preserves the stop condition; M34 remains active but cannot advance to correctness verification |
| D | Determine that the unresolved scope prevents further M34 progress and route the milestone toward one of its frozen terminal outcomes through the approved closure process | Does not itself select an M34 exit; requires the separate M34 exit authority and records |

#### Current consequence

WP6 remains unauthorized and M34.1 remains NO-GO.

#### Risks

A partial entry set may hide product-critical omissions. A full entry approval
without completed owner/definition records would merely move governance
choices into WP6. An indefinite hold may leave M34 without an honest terminal
decision.

#### Dependencies and downstream impact

Depends on recorded ARB outcomes for every applicable prior decision question
and completion of section 8. It determines only the WP6 entry gate. It does
not authorize implementation, Portfolio Home, M34.1, or runtime work.

#### Required ARB decision

Approve full entry, approve an exact bounded subset, keep WP6 NO-GO, or return
M34 to its existing closure authority. Record the choice as a canonical
`ARB_ESCALATION_RESULT` and, when appropriate, a `CHECKPOINT_RESULT` under the
frozen M34 Decision Register rules.

## 3. Decision Dependency Graph

```text
M34-WP5A-DQ-01  audit-domain namespace
        |
        +--> DQ-02  portfolio identity/scope
        |       `--> DQ-03  cross-portfolio exposure
        |
        +--> DQ-07  goal/policy/configuration
        +--> DQ-09  operations composite
        `--> DQ-10  instrument-analysis contract
                    `--> DQ-11  Watchlist membership

DQ-04  classification authority --------+
DQ-05  temporal/failure vocabulary ------+
DQ-08  legacy M32/M33-safe terminology --+--> DQ-06 canonical vocabulary scope
DQ-02, DQ-03, DQ-07, DQ-09, DQ-10, DQ-11+
                                               |
                                               v
                                      DQ-12 WP6 entry decision
```

`M34-WP5A-DQ-08` may be reviewed in parallel with the owner rulings because
M32/M33 are fixed inputs. `M34-WP5A-DQ-06` follows the concept/owner rulings
so vocabulary does not canonize an unresolved boundary. `M34-WP5A-DQ-12` is
always last.

## 4. Impact Matrix

The matrix describes possible governance impact if the ARB approves an option.
It does not authorize the change. `None direct` means the decision can govern
audit interpretation without changing that artifact. `Conditional` means the
selected option determines whether the artifact needs its own approved change
process.

| Decision | Platform Architecture | Domain Constitutions | Glossary | Audit Namespace | M34 | M35+ | Existing implementation | Existing runtime |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `DQ-01` | Conditional if reserved names/boundaries change | None direct | Conditional for alias prohibition/terms | Primary impact | Unblocks or narrows WP6 | Controls naming reuse | None | None |
| `DQ-02` | Conditional if no existing boundary contains the concept | Conditional owner clarification | Likely `Portfolio` term | Portfolio mapping | Owner or exclusion for `SA01` | Establishes future scope language | None | None |
| `DQ-03` | None direct unless boundary interpretation changes | Conditional Portfolio/Wealth clarification | Cross-portfolio exposure term | Owner mapping | Owner or exclusion for `SA02` | Prevents Portfolio/Wealth duplication | None | None |
| `DQ-04` | None direct if Asset/Market boundary is confirmed | Conditional classification clarification | Sector/classification terms | Owner mapping | Enables or excludes sector-dependent review | Controls classification references | None | None |
| `DQ-05` | None direct unless cross-cutting law changes | Conditional source-domain time grammar | Temporal/failure terms | Source owner mapping | Controls trust/failure review | Reusable time-label policy | None | None |
| `DQ-06` | Conditional only for V1-V4 exception/amendment | Domain owners approve their terms | Primary impact | May register audit terms | Controls semantic test basis | Establishes canonical language | None | None |
| `DQ-07` | Conditional if a domain boundary changes | Conditional Portfolio/Decision/Wealth rules | Goal/policy/limit/config terms | Owner mapping | Enables or excludes affected surfaces | Controls configuration governance | None | None |
| `DQ-08` | None; M32/M33 boundaries must remain | Conditional terminology clarification only | Legacy execution/decision terms | Owner/status mapping | Defines positive, negative, or excluded WP6 scope | Prevents predecessor drift | None | None |
| `DQ-09` | Conditional if a new derived concept changes boundaries | Conditional source-status grammar | Operations/status terms | Owner mapping | Enables or excludes Operations claims | Prevents composite-domain drift | None | None |
| `DQ-10` | Conditional only if an existing boundary is changed | Conditional observation/judgment split | Instrument-analysis terms | Owner mapping | Enables or excludes Stock/Watchlist claims | Controls future analysis contracts | None | None |
| `DQ-11` | Conditional if selected owner is outside current boundary | Conditional intent/preference rule | Watchlist term | Owner mapping | Enables or excludes membership claim | Controls future preference/intent semantics | None | None |
| `DQ-12` | None | None | Requires prior approved state | Requires prior approved state | Direct WP6 gate only | Signals inherited limitations | None | None |

No decision in this package requires an implementation or runtime change to be
reviewable. If an ARB option would amend the Platform Architecture, a Domain
Constitution, or the Glossary, that change is a later governed prerequisite;
the option does not edit the artifact by being selected in discussion.

## 5. Governance Risk Register

| Risk ID | Governance risk | Trigger | Consequence | Required control |
| --- | --- | --- | --- | --- |
| `M34-WP5A-GR-01` | Implicit alias becomes a de facto constitutional rename | WP1 labels are used as if reserved domain names | Conflicting owners across M34 and later milestones | Explicit `DQ-01` mapping or exclusion; no inferred aliases |
| `M34-WP5A-GR-02` | A composition surface becomes a hidden domain | Portfolio, Operations, Settings, or Experience is appointed because it groups claims | One-concept/one-owner and dependency law erode | Decide each concept at its existing domain boundary |
| `M34-WP5A-GR-03` | An ownerless concept proceeds to correctness review | WP6 begins with `UNKNOWN_OWNERSHIP` | Auditor effectively appoints an owner | Enforce section 8 owner prerequisite |
| `M34-WP5A-GR-04` | Vocabulary governance canonizes the wrong boundary | Glossary terms are approved before owner decisions | A naming decision hardens an unresolved architecture choice | Review `DQ-06` after concept/owner decisions |
| `M34-WP5A-GR-05` | Ordinary-language exception becomes a private dialect | Unregistered terms carry formulas, status, or authority | Multiple meanings survive under familiar words | Require an explicit ordinary-language list and limits |
| `M34-WP5A-GR-06` | Glossary is overloaded with presentation labels | Every UI phrase is treated as a platform noun | Canonical vocabulary loses precision and maintainability | Register owned concepts; keep presentation synonyms non-normative and linked |
| `M34-WP5A-GR-07` | M32/M33 reopen by terminology rather than evidence | Legacy plan/decision labels are granted canonical authority | Closed NO-GO/STOP decisions are contradicted | Limit `DQ-08` to non-authoritative, negative, or excluded meanings |
| `M34-WP5A-GR-08` | Experience acquires truth ownership | Navigation, refresh completion, or status composition is treated as semantic authority | Duplicate sources of truth and hidden failure | Preserve Experience-renders-truth rule in every decision |
| `M34-WP5A-GR-09` | A partial WP6 scope overstates M34 readiness | Excluded claims are omitted from later summaries | Product readiness appears stronger than audited coverage | Canonical included/excluded family manifest with readiness effect |
| `M34-WP5A-GR-10` | Frozen evidence is rewritten to match a later ruling | WP1-WP5 are edited after ARB review | Audit history and conflict evidence disappear | Use new decision/addendum/supersession records; preserve frozen artifacts |
| `M34-WP5A-GR-11` | An ARB discussion is treated as a decision | Meeting notes or this package are cited without `M34-D-####` approval | Unreviewed governance becomes operative | Require canonical Decision Register and Review Log records |
| `M34-WP5A-GR-12` | A decision silently creates or merges a domain | A novel concept is assigned through broad wording | M34 exceeds scope and bypasses constitutional amendment | Restrict rulings to existing domains or invoke the separate amendment process |
| `M34-WP5A-GR-13` | Deferred governance becomes permanent ambiguity | `Needs Revision` has no owner, scope, or completion evidence | WP6 remains indefinitely blocked without an honest M34 outcome | Every returned question records required revision and checkpoint consequence |

These are governance-review risks, not implementation findings. They do not
allocate `M34-F-####` identifiers or severity.

## 6. Questions for the Architecture Review Board

For every item, the permitted response is exactly **Approve**, **Reject**, or
**Needs Revision**. Approval applies only to the ruling submitted by the ARB,
not to an option preselected by this package.

1. `DQ-01`: Does the submitted namespace ruling exhaustively map or exclude
   the WP1 audit labels without reusing a reserved domain name ambiguously?
2. `DQ-02`: Does the submitted Portfolio ruling give every included
   identity/container concept one existing owner or an explicit exclusion?
3. `DQ-03`: Does the submitted cross-portfolio ruling distinguish Wealth
   exposure from any narrower portfolio-collection projection and appoint one
   existing owner?
4. `DQ-04`: Does the submitted classification ruling distinguish canonical
   classification, witness evidence, analytical grouping, and copied display
   values?
5. `DQ-05`: Does the submitted temporal ruling identify the event, owner, and
   degraded meaning behind every included time/freshness label?
6. `DQ-07`: Does the submitted goal/policy/configuration ruling assign every
   included setting family to one existing owner without creating a Settings
   domain?
7. `DQ-08`: Does the submitted legacy-terminology ruling preserve canonical
   execution-planning NO-GO and `STOP_M33_RUNTIME` without exception?
8. `DQ-09`: Does the submitted operations ruling prevent composition or
   Experience from acquiring source-domain truth and preserve Trust
   independence?
9. `DQ-10`: Does the submitted instrument-analysis ruling separate
   observations, beliefs, derived measures, evaluation, identity, and
   presentation wherever their owners differ?
10. `DQ-11`: Does the submitted Watchlist ruling give membership one bounded
    existing owner and state what membership does not imply?
11. `DQ-06`: After the ownership rulings, does the submitted vocabulary plan
    identify every required Glossary entry, ordinary-language exception, and
    excluded claim without creating a second vocabulary?
12. `DQ-12`: Does the submitted WP6 entry decision name the exact claim-family
    scope, prove every section 8 condition, and preserve M34.1 NO-GO?
13. Package integrity: Are all approved rulings recorded through the frozen
    M34 review/decision lifecycle without modifying WP1-WP5 historical
    evidence?

## 7. Recommended Review Order

1. **Confirm package boundary.** Confirm that WP5A contains decision questions
   only and that `M34-D-####` allocation occurs only after an ARB ruling.
2. **Resolve `DQ-01`.** Every later owner statement needs an unambiguous domain
   namespace.
3. **Resolve foundational scope and source concepts.** Review `DQ-02`,
   `DQ-03`, and `DQ-04` in that order: portfolio scope, cross-portfolio scope,
   then classification authority.
4. **Resolve grouped intent/configuration concepts.** Review `DQ-07` after the
   Portfolio scope decision.
5. **Resolve analytical/composite owner gaps.** Review `DQ-10`, then `DQ-11`,
   and review `DQ-09` once its source-domain labels are unambiguous.
6. **Confirm predecessor-safe terminology.** Review `DQ-08` independently but
   before vocabulary scope. M32/M33 are constraints, not candidate choices.
7. **Resolve temporal/failure language.** Review `DQ-05` after affected source
   owners are known.
8. **Resolve `DQ-06`.** Decide the canonical vocabulary only after every
   included concept has an owner and boundary.
9. **Record and verify governance artifacts.** Create canonical ARB decision
   and review records; complete any separately authorized amendment,
   addendum, or Glossary prerequisite.
10. **Decide `DQ-12`.** WP6 entry is last and uses the verified result of every
    applicable prior decision.

The ARB may review independent questions in one meeting, but the recorded
decisions must respect this dependency order.

## 8. WP6 Entry Conditions

WP6 may begin only when every condition below is objectively true. These
conditions gate entry; they do not redefine WP6.

- [ ] A canonical approved `ARB_ESCALATION_RESULT` exists in the M34 Decision
  Register and references `M34-R-0014`, `M34-R-0015`, and the verified WP5
  evidence used by each ruling.
- [ ] Every applicable `M34-WP5A-DQ-01` through `M34-WP5A-DQ-11` question has
  an approved canonical decision, or an explicit ARB-approved exclusion with
  its M34 readiness effect.
- [ ] The audit namespace has one explicit, exhaustive interpretation; no WP1
  audit label is treated as an inferred constitutional-domain alias.
- [ ] Every claim family admitted to WP6 has exactly one existing semantic
  owner. A source, transport, table, route, component, aggregator, or
  Experience composition is not used as a substitute owner.
- [ ] Every admitted claim has one governing definition under the approved
  hierarchy and vocabulary ruling. `UNKNOWN`, an assumption, implementation
  naming, or a copied field is not used as semantic authority.
- [ ] Every claim family is listed in exactly one of two approved sets:
  `WP6_INCLUDED` or `WP6_EXCLUDED`. No family is omitted by implication.
- [ ] Every exclusion states whether it blocks, narrows, or is immaterial to
  each frozen M34 exit outcome; no excluded claim silently supports readiness.
- [ ] The treatment of `SA27`-`SA30` expressly preserves canonical execution
  planning NO-GO, `STOP_M33_RUNTIME`, non-attribution of legacy activity, and
  the absence of approval authority.
- [ ] Temporal, status, and degraded-state claims admitted to WP6 name the
  event and producing-domain authority that Experience will be evaluated
  against.
- [ ] Cross-domain and composite claims admitted to WP6 retain source-domain
  provenance and do not make Experience or Trust operationally authoritative.
- [ ] Any constitutional amendment, domain-constitution change, ADR, M34
  addendum, or Glossary change required by the selected ARB options is approved
  through its own governing mechanism and effective before WP6 starts.
- [ ] Frozen WP1-WP5 artifacts remain unchanged. Later governance records use
  addendum/supersession and explicit cross-references rather than rewriting
  historical evidence.
- [ ] The M34 Review Log records independent architectural approval and no
  required reference remains `PENDING`.
- [ ] The ARB records an explicit WP6 `CHECKPOINT_RESULT` authorizing the exact
  entry set. Meeting discussion, this package, or absence of objection is not
  authorization.
- [ ] M34.1 remains NO-GO and no decision is interpreted as implementation,
  runtime adoption, Portfolio Home approval, or an M34 exit result.

Failure of any mandatory condition leaves WP6 NO-GO. A `Needs Revision`
response is not partial authorization.

## 9. Explicit Non-Decision and Non-Adoption Statement

M34-WP5A does not:

- choose, recommend, or approve any option in the decision register;
- appoint, create, merge, split, or rename a domain;
- update or amend the Platform Architecture, a Domain Constitution, the
  Glossary, WP1, WP2, WP3, WP4, WP5, the Decision Log, or the M34 working
  registers;
- allocate an `M34-D-####`, `M34-F-####`, evidence, corpus, or review id;
- create a finding, severity, disposition, checkpoint result, M34 exit, or
  M34.1 gate result;
- evaluate a calculation, formula, valuation, return, risk, contribution,
  attribution, freshness result, correctness claim, implementation, or
  runtime behavior;
- redesign a route, contract, service, data model, navigation model, product
  surface, domain, or architecture;
- propose or authorize Portfolio Home, WP6 execution, implementation, or
  runtime work;
- reopen M32 or M33, activate canonical execution planning, or create human
  approval authority; or
- change existing application or runtime behavior.

Every issue remains `PENDING_ARB`. WP6 is not authorized. M34.1 remains
NO-GO.
