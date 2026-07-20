# M36-WP1 - Multiple Portfolio Foundation

**Date:** 2026-07-20

**Document class:** Architecture-level product foundation

**Status:** `APPROVED_AND_CANONICAL`

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

## 1. Purpose

This document defines the technology-independent foundation through which one
M33 actor may own or work with multiple portfolios inside one Product
Workspace without changing portfolio identity, accounting, semantic ownership,
or authority.

In this document, the product phrase “own or work with” does not create a new
semantic-ownership concept. Human identity, workspace membership, portfolio
grants, and point-in-time authority remain governed by M33. Portfolio Identity
and Accounting Scope remain Ledger & Accounting concepts. Product orientation
remains Experience-owned Interaction State.

M36-WP1 is a lower-level refinement of the frozen M35 Product Workspace
Foundation. It uses M35 attachment points and contracts without amending,
superseding, or reopening M35 or any earlier milestone.

## 2. Governing inputs

M36-WP1 is constrained by:

- [Platform Architecture](../architecture/platform_architecture.md),
  especially domain ownership, downward dependencies, the three gates,
  Experience non-ownership, architecture governance, and vocabulary rules;
- [Portfolio Domain Model](../architecture/PORTFOLIO_DOMAIN_MODEL.md),
  especially Portfolio Identity, the Workspace-to-Wealth-to-Portfolio
  hierarchy, portfolio boundaries, lifecycle, and cross-portfolio rules;
- [Canonical Glossary](../GLOSSARY.md), especially Portfolio Identity,
  Accounting Scope, Portfolio Strategy Metadata, Current Selection, Portfolio
  Membership, Portfolio Status, User Preference State, and Interaction State;
- [M33.8 stable human identity and scoped authorization
  foundation](M33_8_stable_human_identity_and_scoped_authorization_foundation.md),
  especially `ActorRef`, `AuthorizationScope`, `Permission`,
  `GrantSourceRef`, `ActorAuthorityFact`, resource status, and fail-closed
  exact-scope validation;
- [M33.9 identity and authorization ownership
  decision](M33_9_identity_authority_provider_selection_and_integration_feasibility.md),
  especially application ownership of workspace membership, portfolio grants,
  inheritance policy, resource status, policy, and point-in-time authority;
- [M34 Decision Register](m34/audit/registers/decision_register.md), especially
  `M34-D-0002`, `M34-D-0003`, `M34-D-0007`, `M34-D-0009`, and
  `M34-D-0010`; and
- [M35 Product Workspace
  Foundation](M35_WP1_Product_Workspace_Foundation.md), especially Workspace
  Identity, Workspace Context, Current Selection, navigation, context
  propagation, Product Contributions, ownership boundaries, and foundation
  invariants.

M35 is treated as approved and frozen under the authority of this milestone.
M36-WP1 changes no M35 text or decision.

## 3. Scope and non-scope

### 3.1 In scope

- the cardinality and meaning of Workspace-to-Portfolio relationships;
- the distinction between Portfolio Identity, Portfolio Lifecycle State,
  Current Selection, source availability, and authority;
- product behavior when a workspace references zero, one, or many portfolios;
- selection and deselection semantics;
- explicit propagation of portfolio context;
- navigation orientation across multiple portfolio references;
- preservation of portfolio and workspace boundaries;
- lifecycle attachment points without lifecycle implementation;
- ownership rules for multiple-portfolio composition; and
- attachment rules for later Product Contributions.

### 3.2 Out of scope

M36-WP1 does not design or authorize:

- a database, schema, persistence model, API, event format, transport, cache,
  frontend, backend, React component, infrastructure, or deployment;
- authentication or authorization implementation;
- membership, grant, inheritance, delegation, sharing, or RBAC policy;
- portfolio creation, transfer, sharing, merge, or closure implementation;
- accounting, ledger, trading, execution, funding, or transaction behavior;
- cross-portfolio analytics, comparison metrics, aggregation formulas, or
  dashboard behavior;
- AI, recommendations, notifications, realtime behavior, or plugin runtime;
- navigation routes, menus, selectors, labels, visual hierarchy, or screen
  design; or
- implementation or runtime adoption of this architecture.

### 3.3 Vocabulary boundary

Before the M36 approval change, the frozen Glossary did not define the
lifecycle state denoted by `active`, `archived`, and `closed` in Portfolio
Domain Model sections 3 and 8. Its existing **Portfolio Status** term means
the Portfolio Intelligence-owned status of portfolio-derived information
under `M34-D-0009`; it is not the lifecycle state of a Portfolio Identity and
M36-WP1 does not redefine it.

The M36 approval change registers exactly one canonical addition:

| Registered term | Exact meaning | Canonical semantic owner | Registration status |
| --- | --- | --- | --- |
| **Portfolio Lifecycle State** | The recorded `active`, `archived`, or `closed` lifecycle state of one Portfolio Identity described by Portfolio Domain Model sections 3 and 8. It qualifies what the portfolio may do next and never rewrites Portfolio Identity, Accounting Scope, ledger history, or evaluation history. M36 adds no unnamed pre-activation state. | Ledger & Accounting, because the state qualifies the Ledger-owned Portfolio Identity and its accounting boundary | `REGISTERED_IN_CANONICAL_GLOSSARY`; the same-change acceptance condition is complete |

Portfolio Lifecycle State is distinct from:

- **Portfolio Identity**, which persists through every state;
- **Portfolio Status**, which remains a Portfolio Intelligence-owned status of
  portfolio-derived information;
- **Current Selection**, which is Experience-owned orientation state;
- source resolution and source availability, which describe whether an exact
  reference can be resolved or its source can currently answer;
- actor authority, which is an M33 point-in-time fact only where an existing
  governed action boundary requires it; and
- transition legitimacy, which is evaluated for a proposed action under
  Portfolio Domain Model section 9 and the Platform Architecture section 7.2
  decision gate and is not encoded in the lifecycle-state value.

In particular, **Active Portfolio is not a canonical concept**. The phrase is
ambiguous and must not appear in an architecture contract:

- **Current Selection** means the zero-or-one portfolio a person is currently
  viewing. It is Experience-owned Interaction State with no business meaning.
- **Portfolio Lifecycle State** such as `active`, `archived`, or `closed` is a
  Ledger & Accounting fact about what the portfolio may do next. It does not
  identify what the person is viewing.
- An actor's authority for a portfolio is an M33 fact. It is neither Current
  Selection nor Portfolio Lifecycle State.

Product copy may use ordinary-language labels only when their referenced
canonical concept is unambiguous. Such labels never enter contracts, identity,
accounting, or authority.

## 4. Canonical concepts

| Concept | Canonical meaning and owner | M36 use | M36 prohibition |
| --- | --- | --- | --- |
| Workspace Identity | Stable Experience-owned reference to one isolated Product Workspace | Identifies the one workspace in the active Workspace Context | Not an account, portfolio, accounting boundary, or authority grant |
| Workspace Context | One explicit Experience-owned interpretation frame | Carries the workspace and optional Current Selection for one interaction | Never becomes business truth or ambient authority |
| Portfolio Identity | Stable identifier of one portfolio container, owned by Ledger & Accounting | Exact reference for every selected or composed portfolio | Never copied, renamed, synthesized, or replaced by a display label |
| Accounting Scope | Ledger-owned boundary for holdings, transactions, cash, and balances | Remains distinct for every portfolio | Never merged because portfolios share a workspace or screen |
| Portfolio Lifecycle State | Canonical state `active`, `archived`, or `closed`, owned by Ledger & Accounting and registered in the canonical Glossary | Qualifies what one Portfolio Identity may do next under the frozen lifecycle | Never means Portfolio Status, Current Selection, source availability, transition approval, or actor authority |
| Portfolio Status | Portfolio Intelligence-owned status of portfolio-derived information under `M34-D-0009` | Retained only to disambiguate it from Portfolio Lifecycle State | Never used as portfolio lifecycle state |
| Portfolio Strategy Metadata | Portfolio Intelligence-owned strategy description | May qualify a source-owned projection | Never owned or corrected by the workspace |
| Current Selection | Experience-owned Interaction State naming the portfolio currently viewed | The sole canonical selection concept; zero or one per Workspace Context | Never means lifecycle `active`, ownership, membership, permission, or default authority |
| Portfolio Membership | Ledger fact that a holding or instrument belongs to one or more Accounting Scopes | Preserved when the same asset appears in multiple portfolios | Never confused with actor membership or workspace composition |
| `ActorRef` | Exact M33 actor identity | Identifies the actor context when relevant | Never replaced by username, email, display name, or generic user id |
| `AuthorizationScope` | Exact M33 authority namespace, workspace id, and portfolio id | Binds an action to one exact portfolio target | Never inferred from Current Selection or navigation |
| `ActorAuthorityFact` | Point-in-time M33 authority result for exact actor, scope, permission, policy, and status | Supplies authority to the responsible gate | Never cached as a property of Workspace Context or Portfolio Identity |
| Product Contribution | M35-declared concern attached through Experience composition | Declares whether it is workspace-scoped or requires an exact portfolio reference | Never becomes a synthetic owner of portfolio concepts |

The word **membership** is therefore always qualified. Portfolio Membership is
an accounting fact. Workspace membership and portfolio grants are M33.9
authorization concerns. Neither is the Workspace-to-Portfolio composition
relationship.

## 5. Canonical relationship model

### 5.1 Structural relationship

```text
one Product Workspace
  identified by one Workspace Identity
  |
  +-- references zero or more Portfolio Identities
  |     |
  |     +-- each belongs to exactly one workspace under the frozen model
  |     +-- each retains exactly one Ledger-owned Accounting Scope
  |     +-- each retains its Ledger-owned Portfolio Lifecycle State and history
  |
  +-- carries zero or one Current Selection
  |     |
  |     +-- NONE, or one exact Portfolio Identity from this workspace
  |
  +-- composes zero or more Product Contributions
        each declares its required workspace and portfolio context
```

The canonical cardinalities are:

- one Product Workspace establishes one isolated Workspace Context;
- a Product Workspace may reference zero, one, or many Portfolio Identities;
- each Portfolio Identity belongs to exactly one workspace under the frozen
  Portfolio Domain Model and M35 relationship;
- each Portfolio Identity retains exactly one Accounting Scope;
- one Workspace Context carries zero or one Current Selection; and
- one M33 `AuthorizationScope` names exactly one workspace and one portfolio.

Multiple portfolios do not change any lower cardinality. They add references
under one workspace; they do not create a shared portfolio, shared ledger,
shared Accounting Scope, combined Portfolio Identity, or second workspace
context.

### 5.2 Portfolio referenceability

A portfolio is referenceable inside one Product Workspace only when all three
of the following resolve together:

1. one exact Ledger-owned Portfolio Identity;
2. that Portfolio Identity's exact one-workspace relationship; and
3. the M35 Context Resolver applying an exact Scope Reference to those source
   facts.

The one-workspace relationship is a Portfolio Identity relationship governed
by the Portfolio Domain Model and preserved by Ledger & Accounting. Experience
may resolve and present the relationship but cannot create, rewrite, or infer
it. Source resolution is an architecture contract, not an API, database,
transport, cache, or availability mechanism.

Referenceability does not depend on Current Selection, source availability,
Portfolio Lifecycle State, generic M33 authority, or a permission to view a
portfolio. None of the frozen inputs defines a generic read or portfolio-view
permission. M36-WP1 does not invent one.

### 5.3 Composition, containment, and authority are distinct

Three relationships must never be collapsed:

1. **Workspace composition:** Experience presents references to Portfolio
   Identities inside one Product Workspace. This owns orientation only.
2. **Portfolio boundary:** the frozen portfolio model constrains one Portfolio
   Identity and its Accounting Scope to one workspace relationship. Experience
   cannot rewrite that relationship.
3. **Actor authority:** the application-owned Identity and Authorization domain
   evaluates workspace membership and portfolio grants and produces exact M33
   facts. Visibility or composition cannot supply this result.

The workspace's list of references is not an accounting membership table and
is not an authorization grant. An M33 resource view used by an existing
governed action may validate its exact target, but it does not determine
whether Portfolio Identity exists, rewrite the one-workspace relationship, or
become the source of Portfolio Identity or Accounting Scope.

### 5.4 Actor cardinality

One `ActorRef` may have valid authority facts for zero, one, or many portfolios.
Each fact remains exact to its workspace, portfolio, permission, policy,
resource status, and validity interval. A workspace-inherited grant is a named
M33 `GrantSourceRef`, not a wildcard and not authority over a portfolio that
was omitted from the evaluated scope.

M36-WP1 does not require one actor per portfolio or one portfolio per actor.
Portfolio sharing and multi-actor policy remain deferred, but the foundation
does not require redesign if separately governed authority later permits them.

### 5.5 Concern separation

| Concern | Meaning in M36-WP1 | Effect on another concern |
| --- | --- | --- |
| Portfolio Identity existence | Ledger & Accounting source fact | Never established or erased by authority, availability, navigation, or selection |
| Workspace-to-Portfolio relationship | Exact one-workspace source relationship for one Portfolio Identity | Never inferred or rewritten by M33, Experience, or a route |
| Source resolution | The M35 Context Resolver validating the exact identity and relationship through its Scope Reference contract | Determines referenceability; creates no authority |
| Source availability | Whether the applicable source can currently answer or supply a projection | May degrade composition; does not prove identity absence or authority denial |
| Current Selection | Zero-or-one Experience orientation reference | Requires a resolved exact identity and relationship; grants nothing |
| Actor authority | Exact M33 fact when an existing governed action boundary requires it | May permit or refuse that action only; never changes referenceability or selection |
| Governed action eligibility | Result of the owning validation and decision-gate rules for one proposed action | Does not become identity, lifecycle state, or general read access |
| Future read-access policy | Not canonically defined by the frozen inputs | Explicitly deferred; never inferred from M33 execution-intent permissions or used for context resolution |

## 6. Multiple-portfolio context model

### 6.1 One interaction, one Workspace Context

Every product interaction has exactly one Workspace Context. Multiple
portfolios exist as explicit references inside that context; they do not create
parallel or nested Workspace Contexts.

| Context concern | Required rule |
| --- | --- |
| Workspace | One exact Workspace Identity is always present |
| Actor | Exact M33 `ActorRef` when an actor is relevant |
| Portfolio referenceability | Exact Portfolio Identity and exact one-workspace relationship resolved by the M35 Context Resolver through its Scope Reference contract; no generic authority input |
| Current Selection | Zero or one referenceable Portfolio Identity belonging to the active workspace |
| Portfolio-scoped contribution | Uses Current Selection or an explicitly supplied referenceable Portfolio Identity, as declared by the contribution |
| Workspace-scoped composition | May carry an explicit bounded set of Portfolio Identity or Scope References without changing Current Selection |
| Domain projection | Preserves portfolio id, Accounting Scope where applicable, canonical owner, provenance, temporal meaning, and degradation |
| Proposed action | Carries the exact target and, only where an existing governed action boundary requires M33, the exact separately valid M33 inputs required by that boundary |

An explicit set of portfolio references in a workspace-scoped composition is
not a multi-valued Current Selection. Current Selection remains zero or one.

### 6.2 Context propagation

The M35 Context Envelope remains the only workspace context carrier. For a
portfolio-scoped interaction it preserves:

- the exact Workspace Identity;
- the exact Portfolio Identity selected or explicitly targeted;
- the distinction between Current Selection and an explicit non-selected
  target;
- the Product Contribution and navigation position;
- source ownership, provenance, time, and degradation for projections; and
- only for a proposed action whose existing governed boundary invokes M33, the
  exact M33 references required by that boundary.

Context is never recovered from a display label, list position, route fragment,
cached last value, first result, recently used portfolio, or currently visible
panel. A transferred Context Envelope must resolve the same workspace and
portfolio relationship as the originating interaction.

### 6.3 Context-resolution mismatch

The following are boundary errors, not fallback opportunities:

- the Current Selection does not belong to the active workspace;
- a portfolio reference resolves under a different workspace;
- a Portfolio Identity is absent, ambiguous, or unknown under its
  Ledger-owned source facts;
- the exact one-workspace relationship is absent, ambiguous, unknown, or does
  not match the active Workspace Identity when the M35 Context Resolver applies
  the Scope Reference contract;
- a contribution requires one portfolio but no Current Selection or explicit
  target exists; or
- a proposed intent target differs from the displayed or declared target.

A context-resolution error removes the affected portfolio-scoped composition
or blocks target formation. It never selects another portfolio automatically,
never consults a generic M33 permission, and never broadens authority.

Source unavailability or degradation is not proof that Portfolio Identity or
its one-workspace relationship is absent. It degrades the affected composition
under the source contract without rewriting the identity, relationship, or
Current Selection.

### 6.4 Governed-action authority mismatch

When, and only when, an existing governed action boundary invokes M33, an
`ActorAuthorityFact` naming a different actor, workspace, portfolio,
permission, policy, grant source, status, or validity interval is unusable for
that action. Missing, denied, stale, ambiguous, or mismatched exact authority
causes the governed action to fail closed.

That refusal does not make Portfolio Identity unknown, alter its workspace
relationship, clear Current Selection, or make a source unavailable. M36-WP1
does not extend M33's execution-intent permissions into generic read or
portfolio-view permissions.

## 7. Ownership model

| Concern | Canonical owner or exact governing boundary | M36 responsibility | M36 non-ownership |
| --- | --- | --- | --- |
| Workspace Identity, Workspace Context, Current Selection, navigation, and composition | Experience Platform under M35 | Preserve isolation and orientation across portfolio references | No financial, strategy, lifecycle, or authority truth |
| Portfolio Identity, its one-workspace relationship, and Accounting Scope | Ledger & Accounting under M34 and the Portfolio Domain Model | Preserve exact references, the exact relationship, and separate scopes | No Experience or authority mutation, inferred relationship, or duplicate identity |
| Portfolio Lifecycle State | Ledger & Accounting under the canonical Glossary registration recorded in section 3.3 | Preserve the exact state supplied for one Portfolio Identity | No Experience state transition, transition approval, availability inference, or use as Current Selection |
| Holdings, transactions, cash, balances, and ledger history | Ledger & Accounting | Present source-owned projections only | No workspace calculation or cross-portfolio write |
| Portfolio Strategy Metadata and portfolio-derived knowledge | Portfolio Intelligence | Present source-owned projections with provenance | No workspace strategy or metric semantics |
| Whole-wealth aggregation, goals, and life-level meaning | Wealth Intelligence | Attach a source-owned projection at Workspace Scope when later designed | No workspace-owned net worth or aggregate truth |
| Actor identity and authentication | Frozen M33 provider boundary | Carry exact M33 references when required | No UI identity inference |
| Workspace membership, portfolio grants, resource status, policy, and point-in-time authority | Application-owned Identity and Authorization domain under M33.9 | Consume exact results only when an existing governed action boundary invokes M33 | No identity-, relationship-, source-resolution-, selection-, navigation-, visibility-, or generic-read-derived permission |
| Product Contribution contract and composition relationship | Experience Platform under M35 | Declare required scope and preserve every constituent owner | No synthetic semantic owner |
| Portfolio lifecycle transition legitimacy | Not allocated by M36; Portfolio Domain Model section 9 validation and the Platform Architecture section 7.2 decision gate are the exact governing boundaries for a proposed action | Route proposed intent to those existing boundaries only | No new transition owner or rule, Experience decision, mutation, or inference from Portfolio Lifecycle State alone |

The workspace may compose many source-owned projections. Composition changes
neither their owner nor their meaning. If a future composition introduces a new
business concept, that concept requires its own governed canonical owner before
M36 attachment rules may be used.

## 8. Workspace behavior across multiple portfolios

### 8.1 Zero referenced portfolios

The Product Workspace remains a valid isolated product context. Workspace-
scoped orientation may remain available, but portfolio-scoped Product
Contributions are inapplicable. The workspace does not create an empty
portfolio, placeholder identity, or inferred default.

### 8.2 One referenced portfolio

The same multiple-portfolio foundation applies. The sole reference is not
automatically Current Selection. An explicit selection or exact validated deep
entry is still required where a Product Contribution requires Current
Selection.

### 8.3 Many referenced portfolios

The workspace may orient among the references and compose workspace-scoped
projections. It does not:

- combine Accounting Scopes;
- treat the references as one strategy or portfolio;
- choose a primary, default, first, largest, newest, or most recently used
  portfolio by architecture;
- calculate net worth, total exposure, performance, risk, or comparison;
- propagate state from one portfolio to another; or
- infer that authority for one portfolio applies to another.

Any cross-portfolio derived meaning remains owned by its existing source
domain. Wealth-level aggregation is not workspace computation.

### 8.4 Loss or qualification of a reference

The following remain distinct:

| State or qualification | Exact effect |
| --- | --- |
| `unknown` Portfolio Identity | Exact identity cannot be established under the Ledger & Accounting source facts; the reference does not resolve |
| relationship mismatch | Exact identity exists, but its one-workspace relationship does not match the active Workspace Identity; the reference does not resolve in this context |
| source `unavailable` | The source cannot currently answer; affected composition degrades, but identity and relationship are not declared absent |
| `degraded` | A source or projection carries an explicit quality limitation; identity, relationship, lifecycle state, and authority remain separately evaluated |
| `unauthorized` governed action | Exact authority validation failed for that action; identity, relationship, Current Selection, and source availability do not change |
| `archived` or `closed` | Exact Portfolio Lifecycle State; identity and history persist, while action eligibility remains governed separately |

No frozen input defines a generic read-access policy. Portfolio Lifecycle State
does not by itself decide readability, source availability, selection, or
actor authority, and M33 execution-intent permissions are not used as a
substitute.

Current Selection returns to none only when the exact Portfolio Identity or
its exact one-workspace relationship no longer resolves when the M35 Context
Resolver applies the Scope Reference contract. Source unavailability,
degradation, an unauthorized
governed action, or `archived` or `closed` state alone does not clear it. When
clearing is required, the workspace does not fall back to another portfolio.
Ledger history and Portfolio Identity remain unchanged.

## 9. Portfolio selection model

### 9.1 Canonical state

```text
Current Selection = NONE | one exact Portfolio Identity
```

Current Selection is scoped to one Workspace Context and owned entirely by
Experience Platform. It records orientation only.

### 9.2 Permitted transitions

| Previous selection | Trigger | Result | Prohibited implication |
| --- | --- | --- | --- |
| `NONE` | Explicit human orientation to an exact Portfolio Identity whose one-workspace relationship the M35 Context Resolver resolves through the Scope Reference contract | That Portfolio Identity becomes Current Selection | No authority, ownership, lifecycle, availability, or accounting change |
| `NONE` | Exact deep entry whose Portfolio Identity and one-workspace relationship resolve | The exact target may become Current Selection | No route-derived permission, generic M33 check, or fuzzy resolution |
| Portfolio A | Explicit orientation to Portfolio B whose exact same-workspace relationship resolves | Portfolio B becomes Current Selection | No mutation, authority check, transfer, or state merge between A and B |
| One portfolio | Explicit clear or departure from portfolio scope | `NONE` | No portfolio deletion, archival, or closure |
| One portfolio | The exact Portfolio Identity or its one-workspace relationship no longer resolves when the M35 Context Resolver applies the Scope Reference contract | `NONE`; affected composition becomes inapplicable | No automatic selection of another portfolio; unavailability, degradation, lifecycle state, or action denial alone does not trigger this transition |

Whether selection is retained across sessions, devices, or product entries is
not defined. A future preference may propose an initial orientation only under
the M35 User Preference State boundary and after exact context validation. It
can never become authority or an architecture-level default portfolio.

### 9.3 Selection and action

Current Selection may nominate the portfolio a person is viewing or proposing
to act upon. It may not authorize that action. When an existing governed action
boundary invokes M33, the Intent Envelope and M33 boundary must bind the exact
`ActorRef`, target, `AuthorizationScope`, existing `Permission`,
`GrantSourceRef`, point-in-time `ActorAuthorityFact`, resource status, and
applicable validation result.

If selected context and required authority context disagree, that governed
action stops. The UI does not win, the newest value does not win, and no scope
is widened. The refusal does not clear Current Selection or change Portfolio
Identity, its workspace relationship, Portfolio Lifecycle State, or source
availability. An action for which the frozen M33 vocabulary defines no
permission receives no invented generic permission from M36-WP1.

## 10. Navigation model

M36 refines the frozen M35 navigation attachment classes without defining a
route tree or interface.

```text
Workspace Scope
  orientation among explicit same-workspace Portfolio Identity references
  |
  +-- Portfolio Scope
  |     orientation within zero or one Current Selection
  |
  +-- Object Focus
  |     one source-owned object within an explicit portfolio context
  |
  +-- Contribution Focus
        one Product Contribution with declared context requirements
```

Navigation obeys these laws:

1. Workspace Scope remains inside one Workspace Context.
2. A portfolio navigation position references an exact Portfolio Identity,
   never a name, ordinal, icon, route, or cached object.
3. Reaching or displaying a portfolio does not prove membership, permission,
   Portfolio Lifecycle State, governed-action eligibility, or authority.
4. Portfolio Scope consumes Current Selection explicitly.
5. Workspace-scoped navigation may refer to many portfolios without creating a
   multi-valued Current Selection.
6. Moving between portfolio positions changes only Experience Interaction
   State.
7. Deep entry reconstructs and validates the same workspace/portfolio context
   as entry through Workspace Scope.
8. Navigation never reads across another workspace or silently repairs a
   context mismatch.
9. Removing one portfolio reference leaves the workspace navigation topology
   valid.
10. Visual ordering, naming, grouping, favoriting, and recent-history behavior
    remain product-design or personalization decisions outside M36-WP1.

## 11. Portfolio boundary rules

1. Every Portfolio Identity retains its own Accounting Scope.
2. Every holding, transaction, cash fact, balance, and ledger event remains in
   its exact Accounting Scope.
3. The same canonical asset held by several portfolios remains one Asset
   Identity referenced by separate portfolio holdings; it is not duplicated or
   merged by the workspace.
4. No portfolio directly reads, funds, adjusts, or mutates another portfolio's
   source state.
5. Any future movement between portfolios must use explicit mirrored Ledger &
   Accounting events through the existing Platform ingestion or decision gate,
   as required by the Portfolio Domain Model; M36 defines no transfer behavior.
6. Cross-portfolio presentation preserves each Portfolio Identity, source,
   provenance, time, Portfolio Lifecycle State, and degraded state.
7. Cross-portfolio comparison does not create a common strategy, benchmark,
   policy, performance result, or semantic owner.
8. Cross-workspace composition is prohibited by default and cannot be enabled
   through Current Selection.
9. Portfolio names and navigation positions never serve as identity.
10. Portfolio closure or archival never deletes or re-keys identity or history.

## 12. Portfolio lifecycle attachment points

M36 does not redefine the lifecycle in the Portfolio Domain Model. It defines
only how the workspace may attach to the registered Ledger & Accounting-owned
Portfolio Lifecycle State. The same-change Glossary-registration condition is
complete. State observation is distinct from deciding whether a proposed
transition is legitimate; transition intent remains subject to Portfolio
Domain Model section 9 and the Platform Architecture section 7.2 decision
gate.

| Existing lifecycle concern | Workspace attachment effect | Retained boundary |
| --- | --- | --- |
| Create | A new Portfolio Identity becomes referenceable only after the M35 Context Resolver resolves the exact identity and its exact one-workspace relationship through the Scope Reference contract | No authority input, automatic selection, lifecycle-state inference, or authority grant |
| Activate | Ledger & Accounting records `active` as the Portfolio Lifecycle State after the governed transition | `active` is not Current Selection, source availability, general action eligibility, or authority |
| Archive | Ledger & Accounting records `archived` as the Portfolio Lifecycle State; identity and history remain addressable | No generic read policy or workspace decision that archival permits or forbids an action |
| Clone | The clone is a new Portfolio Identity with a separate Accounting Scope and no shared history | No inherited Current Selection, grant, or authority by implication |
| Merge | Ledger & Accounting preserves the source and surviving Portfolio Identities, Accounting Scopes, and historical boundaries; any forward movement uses explicit mirrored ledger events | No identity rewrite, history blend, or automatic selection change |
| Close | Ledger & Accounting records `closed` as the Portfolio Lifecycle State; identity, ledger, history, and evaluation remain addressable under their canonical source contracts | `closed` is not deleted, Current Selection, unavailability, or action denial by itself |
| Import | Imported reality enters only through existing ingestion and accounting gates | No workspace ingestion or authority shortcut |
| Export | Source truth may be projected through its existing governed boundary | No change to Current Selection, ownership, or authority |

Relocating a portfolio between workspaces is not defined by the frozen
lifecycle and is not introduced by M36-WP1. A navigation or preference action
cannot perform such a relocation.

## 13. Future attachment model

Future concerns attach through frozen M35 Product Contribution contracts:

| Future concern | M35 attachment | M36 requirement | Deferred behavior |
| --- | --- | --- | --- |
| Portfolio orientation | Workspace Scope and Portfolio Scope | Exact Portfolio Identity and exact one-workspace relationship resolved by the M35 Context Resolver through the Scope Reference contract, plus zero-or-one Current Selection; no generic authority dependency | Visual selector, ordering, labels, recents, favorites, and read-access policy |
| Portfolio comparison | Workspace Scope with an explicit bounded set of Portfolio Identity references | Preserve every source owner, metric definition, provenance, time, and degradation | Comparison metrics and product behavior |
| Wealth overview | Workspace Scope using a Wealth Intelligence-owned projection | Workspace presents but does not calculate aggregation | Net-worth, exposure, allocation, and goal behavior |
| Portfolio lifecycle administration | Governed Product Operations and Intent Router | Explicit target, Portfolio Domain Model section 9 validation, the Platform decision gate, and exact M33 authority only where an existing permission and action boundary require it | Commands, workflows, approvals, read-access policy, and persistence |
| Cross-portfolio proposed intent | Intent Router with every affected portfolio identified separately | Exact context and, where an existing governed boundary invokes M33, exact authority validation for each affected target; no composite wildcard scope | Transfer, funding, trading, execution, and transaction behavior |
| Team or shared work | Workspace Context `ActorRef` and M33 authority contracts | No navigation-derived access and no implicit grant inheritance | Sharing, delegation, RBAC, collaboration, and audit behavior |
| Dashboards or plugins | Workspace- or Portfolio-scoped Product Contribution | Declared context cardinality and source-owner mapping | Layout, metrics, packaging, installation, trust, and runtime |
| Personalization | M35 Interaction State Contract | Preference may influence orientation only after validation | Preference catalog, persistence, synchronization, and behavior |

A later Product Contribution must declare whether it requires:

- workspace context only;
- an optional Current Selection;
- exactly one Current Selection or explicit Portfolio Identity; or
- an explicit bounded set of Portfolio Identity references for presentation.

That declaration controls applicability only. It does not create authority,
read access, aggregation meaning, or a new portfolio concept.

## 14. Architectural decision register

These are M36-WP1 architecture decisions. They do not amend higher-level
governance and do not constitute implementation approval.

| Decision | Ruling | Reason |
| --- | --- | --- |
| `M36-WP1-A01` | Active Portfolio is rejected as a canonical concept; the registered Ledger & Accounting-owned Portfolio Lifecycle State and Experience-owned Current Selection remain separate | Prevents Experience orientation from acquiring lifecycle or source-domain meaning without redefining the existing Portfolio Status term |
| `M36-WP1-A02` | One Product Workspace references zero or more Portfolio Identities; one Workspace Context carries zero or one Current Selection | Preserves M35 cardinality while enabling multiple portfolios |
| `M36-WP1-A03` | Every Portfolio Identity retains one separate Accounting Scope and its existing one-workspace relationship | Prevents shared-ledger or duplicate-identity models |
| `M36-WP1-A04` | Current Selection is explicit, has no architecture default, and never changes portfolio truth | Prevents ambient context and hidden product policy |
| `M36-WP1-A05` | Portfolio Identity existence, the one-workspace relationship, M35 Context Resolver and Scope Reference resolution, source availability, Current Selection, Portfolio Lifecycle State, and actor authority are independent concerns | Prevents navigation, availability, lifecycle, or authority from rewriting identity, relationship, access, or ownership |
| `M36-WP1-A06` | Exact M33 actor, workspace, portfolio, permission, grant, policy, status, and time inputs are required only where an existing governed action boundary invokes M33; that action fails closed on invalid authority | Preserves frozen M33 authority without inventing generic read or portfolio-view permission or making authority a context-resolution dependency |
| `M36-WP1-A07` | A workspace-scoped composition may reference many portfolios while Current Selection remains zero or one | Supports comparison and overview attachment without redefining selection |
| `M36-WP1-A08` | Cross-portfolio composition preserves constituent ownership and creates no aggregate truth | Keeps Wealth, Portfolio, Ledger, and Experience responsibilities separate |
| `M36-WP1-A09` | Portfolio Lifecycle State is a registered Ledger & Accounting-owned canonical fact; Portfolio Identity and history survive every transition, while transition legitimacy remains a separate governed-action determination | Keeps workspace state from rewriting lifecycle, history, or action eligibility |
| `M36-WP1-A10` | Future concerns attach only through M35 contracts with declared portfolio-context requirements | Enables later capabilities without foundation redesign |

## 15. Foundation invariants

M36-WP1 is conformant only while all of the following remain true:

1. Every product interaction has one explicit Workspace Context.
2. A workspace may reference zero, one, or many Portfolio Identities.
3. Each Portfolio Identity retains exactly one Accounting Scope.
4. Each Portfolio Identity belongs to exactly one workspace under the frozen
   relationship model.
5. Current Selection is always none or one exact same-workspace Portfolio
   Identity.
6. Current Selection remains Experience-owned Interaction State with no
   business meaning.
7. When Portfolio Lifecycle State is recorded, its vocabulary is exactly
   `active`, `archived`, or `closed`; it is owned by Ledger & Accounting,
   M36 introduces no additional state, and its canonical Glossary registration
   is complete.
8. Portfolio Lifecycle State never means Portfolio Status, Current Selection,
   source availability, permission, transition approval, or authority.
9. Referenceability depends only on exact Portfolio Identity, its exact
   one-workspace relationship, and the M35 Context Resolver applying the Scope
   Reference contract.
10. Source availability, degradation, unauthorized action, Portfolio Lifecycle
    State, and relationship mismatch remain distinct qualifications.
11. Current Selection resolution never requires generic M33 authority and is
    cleared without fallback only when exact identity or relationship no longer
    resolves.
12. Selection, visibility, navigation, ordering, and personalization never
    grant authority.
13. Authority never determines Portfolio Identity existence or rewrites its
    one-workspace relationship, Portfolio Lifecycle State, or Current
    Selection.
14. Where an existing governed action invokes M33, its authority result always
    binds an exact actor, workspace, portfolio, existing permission, grant
    source, policy, resource status, and validity interval and fails closed.
15. Authority for one portfolio never implies authority for another.
16. A workspace-inherited grant never becomes an unbounded or inferred scope.
17. No workspace context, contribution, or composition duplicates Portfolio
    Identity, Accounting Scope, strategy, lifecycle, or authority ownership.
18. A multi-portfolio presentation preserves every constituent identity,
    owner, source, provenance, time, lifecycle state, and degradation.
19. Experience computes no portfolio or cross-portfolio business number.
20. Missing selection never causes arbitrary or automatic portfolio selection.
21. A context mismatch fails explicitly and never crosses a workspace boundary.
22. Portfolio lifecycle changes never rewrite identity or historical Ledger &
    Accounting records.
23. Every proposed action leaves Experience through its existing governed
    validation and decision-gate boundary.
24. Implementation and runtime authority remain external to M36-WP1.

## 16. Explicit deferrals

M36-WP1 intentionally does not determine:

- how portfolio references, Current Selection, or context are stored,
  transported, synchronized, restored, or cached;
- how a workspace or portfolio is created, provisioned, transferred, archived,
  merged, cloned, imported, exported, or closed at runtime;
- which Portfolio Lifecycle States permit which read or write operations;
- any generic read-access or portfolio-view policy, because none is
  canonically defined by the frozen inputs and M33 execution-intent permissions
  must not be repurposed for it;
- which portfolio, if any, is suggested when a workspace opens;
- whether a remembered selection exists or how long it lasts;
- how portfolio names, ordering, grouping, favorites, recents, or search work;
- how workspace membership, portfolio grants, inheritance, delegation,
  revocation, sharing, or collaboration work;
- how cross-portfolio comparison, aggregation, wealth, analytics, dashboards,
  notifications, AI, trading, execution, or transfers behave;
- which Product Contributions are implemented or enabled; or
- any database, API, event, frontend, backend, infrastructure, deployment,
  identity-provider, authorization, or runtime design.

Every deferral has an existing attachment or ownership boundary. None is
silently answered by selection, navigation, or workspace composition.

## 17. Architectural approval and completion criteria

The second independent architectural review returned `APPROVED`. It confirmed
that `M36-ARB-F01` and `M36-ARB-F02` are resolved, subject only to same-change
canonical registration of Portfolio Lifecycle State. That registration is
complete in the canonical Glossary as part of this approval change. M36-WP1 is
therefore approved and canonical.

The approval confirms that:

- it preserves the frozen M35 Workspace model and cardinalities;
- Active Portfolio does not become a competing canonical concept;
- Portfolio Identity, Accounting Scope, Portfolio Strategy Metadata, Current
  Selection, Portfolio Status, and M33 authority retain their existing owners
  and meanings;
- Portfolio Lifecycle State has one exact meaning and Ledger & Accounting
  owner, remains distinct from transition legitimacy, and is registered in the
  canonical Glossary in the same accepted change;
- one actor can work with multiple portfolios without generic or UI-derived
  authority;
- zero, one, and many portfolio references behave coherently;
- Current Selection remains zero or one and has no implicit default;
- context propagation is explicit and fail-closed;
- portfolio referenceability and Current Selection resolution depend only on
  exact identity, exact one-workspace relationship, and the M35 Context
  Resolver applying the Scope Reference contract, never generic authority;
- unavailable, unauthorized, unknown, archived, closed, degraded, and
  relationship-mismatched remain distinct;
- navigation and visibility remain separate from authority;
- cross-portfolio composition creates no business truth or synthetic semantic
  owner;
- lifecycle attachment does not redefine lifecycle behavior;
- future Product Contributions attach without changing the foundation; and
- no implementation, runtime, or governance authority is claimed.

## 18. Retained non-authorizations

This document creates no:

- implementation plan, implementation authority, source-code change, or data
  migration;
- runtime plan, runtime authority, deployment, or product enablement;
- database, schema, API, event, frontend, backend, infrastructure, or
  technology decision;
- authentication, membership, grant, sharing, delegation, or authorization
  implementation;
- portfolio, workspace, actor, grant, authority fact, Current Selection, ledger
  event, or lifecycle transition;
- trading, execution, transfer, analytics, aggregation, AI, dashboard, or
  plugin behavior;
- new constitutional domain, business-truth owner, authority source, or
  unregistered product noun; Portfolio Lifecycle State is the single canonical
  vocabulary addition completed by the M36 approval change;
- change to any frozen M29-M35 artifact or decision; or
- amendment to Platform Architecture, M33, M34, or M35 beyond the required
  canonical Glossary registration.

Retained state:

```text
M29-M35:                  CLOSED AND FROZEN
M36:                      CLOSED AND CANONICAL
M36-WP1 architecture:     APPROVED
M36-WP2 remediation:      COMPLETE
Portfolio Lifecycle State: REGISTERED IN CANONICAL GLOSSARY
Product implementation:  NOT AUTHORIZED
Runtime adoption:         NOT AUTHORIZED
Implementation authority: NONE
Runtime authority:         NONE
```

The recommended next architecture milestone is M37 - Universal Asset Search
Foundation. This recommendation creates no M37 implementation or runtime
authority, and no product-capability work follows by implication.
