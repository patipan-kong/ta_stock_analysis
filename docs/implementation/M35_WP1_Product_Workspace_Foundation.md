# M35-WP1 - Product Workspace Foundation

**Date:** 2026-07-20

**Document class:** Architecture-level product foundation

**Status:** `PROPOSED_FOR_SECOND_ARCHITECTURAL_REVIEW`

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

## 1. Purpose

This document defines the technology-independent foundation through which a
person encounters the product. It establishes the minimum workspace model,
context model, state model, navigation topology, logical services, product
contracts, ownership boundaries, and extension points required by later
product concerns.

The Product Workspace is not a new constitutional domain. It is the
Experience Platform's operating context over concepts owned by the existing
platform domains. It provides isolation, orientation, composition, and intent
routing. It does not acquire the meaning or authority of anything it presents.

This document is a lower-level refinement under Platform Architecture section
11 G3. It does not amend, supersede, reinterpret, or reopen any frozen M34
artifact or earlier architectural decision.

## 2. Governing inputs

The foundation is constrained by:

- [Platform Architecture](../architecture/platform_architecture.md),
  especially sections 4, 5, 6.9, 7, 8, 11, and 12;
- [Portfolio Domain Model](../architecture/PORTFOLIO_DOMAIN_MODEL.md),
  especially Portfolio Identity, the Workspace-to-Wealth-to-Portfolio
  hierarchy, and workspace isolation;
- [M33.8 stable human identity and scoped authorization
  foundation](M33_8_stable_human_identity_and_scoped_authorization_foundation.md),
  especially `ActorRef`, `AuthenticationEventRef`, `ActorStatusFact`,
  `AuthorizationScope`, `Permission`, `GrantSourceRef`,
  `ActorAuthorityFact`, and the identity-validation contracts;
- [M33.9 identity and authorization ownership
  decision](M33_9_identity_authority_provider_selection_and_integration_feasibility.md),
  especially the managed identity-provider boundary and the application-owned
  Identity and Authorization domain;
- [M34 semantic mapping](m34/audit/reports/M34_WP6A_semantic_mapping.md),
  especially the source-domain, presentation, Current Selection, and
  interaction-state boundaries;
- [M34 Decision Register](m34/audit/registers/decision_register.md), especially
  `M34-D-0002`, `M34-D-0007`, `M34-D-0009`, `M34-D-0010`, and
  `M34-D-0011`; and
- [Canonical Glossary](../GLOSSARY.md), including Portfolio Identity,
  Accounting Scope, Current Selection, Watchlist Membership, User Preference
  State, and Interaction State.

Where this document refers to a domain-owned concept, that concept retains its
existing canonical meaning and owner. No composition, label, navigation
relationship, context value, or extension may become a competing definition.

## 3. Scope and non-scope

### 3.1 In scope

- the canonical responsibility of the Product Workspace;
- the logical objects needed to establish product context;
- product navigation structure without routes or screen design;
- categories and invariants of workspace state;
- logical workspace services without deployment or implementation choices;
- contracts between the workspace and Product Contributions that preserve the
  ownership of every domain-owned concept;
- extension rules and governed attachment points; and
- explicit ownership and non-ownership boundaries.

### 3.2 Out of scope

This milestone does not design or authorize:

- Portfolio Intelligence, recommendations, execution, trading, charts,
  analytics, AI behavior, notifications, realtime behavior, broker
  integration, pricing, or the Asset Registry;
- screens, dashboards, routes, visual hierarchy, interaction details, or
  presentation copy;
- APIs, database schemas, events, protocols, infrastructure, deployment,
  frameworks, React or other frontend code, or backend code;
- identity-provider, tenancy, membership, RBAC, billing, or organizational
  policy design;
- any domain calculation, financial truth, judgment, evidence, or
  authorization rule; or
- implementation or runtime adoption of this architecture.

Future product concerns are named only where necessary to prove that the
foundation has a lawful attachment point. Their behavior remains deferred.

### 3.3 Vocabulary governance

The canonical Glossary already defines **Capability** as one queryable behavior
fact granted by an asset definition. M35-WP1 does not overload that term. A
concern that attaches to the Product Workspace is instead a **Product
Contribution**.

The following load-bearing terms are explicitly proposed canonical additions.
They are normative within this architecture proposal. Architectural acceptance
requires their registration in the canonical Glossary in the same governed
change, as required by Platform Architecture section 11 V1-V2. This proposal
does not alter the meaning of any frozen term.

| Proposed canonical term | Exact proposed meaning |
| --- | --- |
| Product Workspace | The Experience Platform operating context that establishes one isolated product context and composes references, projections, navigation, interaction state, and proposed-intent routing without owning source-domain truth or authority. |
| Workspace Identity | A stable Experience-owned reference to one Product Workspace; not a person, account, portfolio, tenant implementation, or authority grant. |
| Workspace Boundary | The Experience-owned isolation rule that prevents context and presentation state from crossing Product Workspaces by default. |
| Workspace Context | The explicit Experience-owned frame that identifies the one Product Workspace and applicable selection, focus, contribution, actor reference, navigation, provenance, temporal, degradation, and authority references needed to interpret one product interaction. |
| Focus Reference | An Experience-owned interaction reference to the domain object presently in view; it neither owns nor mutates the object. |
| Product Contribution | A declared product concern attached through an Experience-owned composition contract. It has no synthetic semantic ownership; every concept it uses retains exactly one canonical owner. |
| Intent Reference | An Experience-owned reference to proposed human intent routed to the responsible gate; it is not approval, instruction, execution, or a domain record. |
| Workspace Descriptor | The architecture contract that identifies one Product Workspace and its isolation boundary. |
| Context Envelope | The architecture contract that carries one explicit Workspace Context without converting identity or authority references into authority. |
| Scope Reference | The architecture contract that preserves a referenced workspace, Portfolio Identity, Accounting Scope, or domain-object identity and canonical owner. |
| Product Contribution Descriptor | The architecture contract that declares one Product Contribution, its attachment requirements, and the canonical owner of every concept it uses. |
| Navigation Contribution | The architecture contract that declares an orientation relationship at an allowed attachment class and owns no displayed business concept. |
| Projection Contract | The architecture contract that preserves source ownership, identity, provenance, temporal meaning, quality, and degradation for displayed domain information. |
| Intent Envelope | The architecture contract that carries proposed intent and the exact identity, scope, permission, authority, and target-gate references required by its governing boundary. |
| Interaction State Contract | The architecture contract that confines interaction and preference state to Experience-owned meaning and an extension-owned namespace. |
| Extension Manifest | The revision-identified architecture declaration that combines one contribution descriptor, its attachments, context requirements, namespace, dependencies, degradation behavior, concept-owner mapping, and foundation compatibility claim; it is not a package or installation mechanism. |
| Workspace Extension | A bounded Product Contribution attached by declaration; it is not necessarily a plugin, package, deployment unit, screen, or service. |
| Product Attachment Class | One of Workspace Scope, Portfolio Scope, Object Focus, Contribution Focus, or Governed Product Operations; it classifies an orientation relationship and does not define a route or feature. |
| Workspace Directory | The logical responsibility for resolving available Workspace Identities from an authoritative operational source. |
| Context Resolver | The logical responsibility for validating and assembling one Workspace Context. |
| Selection Coordinator | The logical responsibility for maintaining Current Selection within the active Product Workspace. |
| Navigation Composer | The logical responsibility for assembling orientation from valid Navigation Contributions. |
| Contribution Catalog | The logical responsibility for describing available Product Contribution contracts and attachment points. |
| Projection Coordinator | The logical responsibility for requesting and presenting source-owned projections while preserving provenance and degradation. |
| Interaction State Coordinator | The logical responsibility for maintaining Experience-owned context, preference, and namespaced contribution state. |
| Intent Router | The logical responsibility for delivering proposed human intent to its responsible constitutional gate without deciding or executing it. |
| Extension Governor | The logical responsibility for validating extension declarations against workspace contracts without granting implementation, runtime, or domain authority. |
| Degradation Coordinator | The logical responsibility for surfacing unavailable or qualified contributions without silent substitution. |

Existing canonical terms, including Portfolio Identity, Accounting Scope,
Current Selection, Capability, User Preference State, and Interaction State,
retain their frozen meanings and are not redefined here.

## 4. Architectural principles

1. **Product context is explicit.** Every product interaction occurs within a
   declared workspace context. No consumer may infer scope from an ambient
   route, cache, or previously visited surface.
2. **Composition does not transfer ownership.** A workspace may present or
   coordinate domain-owned concepts but never becomes their semantic owner.
3. **Navigation expresses orientation, not authority.** Being able to reach a
   Product Contribution does not grant permission to use it and does not alter
   state.
4. **Intent is routed, never executed by the workspace.** The workspace may
   capture a person's proposed intent and deliver it to the owning gate. It
   may not validate, approve, or execute domain action on its own.
5. **Extensions are additive and bounded.** A Product Contribution attaches
   through a declared contract. It cannot replace foundation behavior, weaken
   an invariant, or depend on undocumented ambient state.
6. **Source truth remains outside presentation.** Financial facts,
   observations, knowledge, judgment, and evaluation remain owned by their
   constitutional domains and are consumed as read-only projections.
7. **Failure is visible and contained.** An unavailable contribution degrades
   its own attachment. It does not silently substitute data or prevent the
   rest of the workspace from remaining coherent.
8. **The model is cardinality-neutral.** The same foundation supports one or
   many workspaces, portfolios, assets, M33 actors, and extensions without a
   new root model.
9. **Technology is replaceable.** Every object and service in this document is
   logical. No framework, process boundary, persistence form, or transport is
   implied.
10. **No foundation object grants authority.** Authorization is always an
    input from its governing source, never a consequence of context,
    visibility, selection, navigation, or extension registration.

## 5. Workspace domain model

### 5.1 Canonical relationship

```text
Product Workspace
  establishes one isolated product context
  |
  +-- references zero or more available Portfolio Identities
  |     each retains one Ledger-owned Accounting Scope
  |
  +-- carries zero or one Current Selection
  |     Experience interaction state only
  |
  +-- composes zero or more Product Contributions
  |     each preserves the canonical owner of every constituent concept
  |
  +-- carries namespaced Interaction and User Preference State
  |
  +-- routes proposed intent to an existing constitutional gate
        never directly to domain truth
```

The Product Workspace is the outer product context already anticipated by the
Portfolio Domain Model. It is an isolation and composition boundary, not an
accounting boundary, strategy, portfolio, wealth aggregate, product domain,
authorization boundary, or new constitutional domain.

### 5.2 Minimal logical objects

| Object | Architectural meaning | Owner | Prohibited meaning |
| --- | --- | --- | --- |
| Workspace Identity | Stable reference to one isolated product context | Experience Platform operational shell | Not a person, account, portfolio, ledger, tenant implementation, or authorization grant |
| Workspace Boundary | Rule that context and presentation do not combine state across workspaces by default | Experience Platform operational shell | Not an accounting or asset-identity boundary |
| Workspace Context | Explicit frame that accompanies product composition and intent | Experience Platform | Not source-domain truth or proof of access |
| Current Selection | Portfolio currently being viewed, if any | Experience Platform, per `M34-D-0002` | No change to Portfolio Identity or Accounting Scope |
| Focus Reference | Optional reference to the domain object presently in view | Experience Platform interaction state | No ownership or mutation of the referenced object |
| Product Contribution | Declared product concern made available at a governed attachment point | Experience owns the contribution contract and composition relationship; every constituent concept remains owned by its canonical source domain or by Experience when it is canonically Interaction State | No synthetic semantic owner; not proof of authorization, availability, or correctness |
| Interaction State | Bounded state of product interaction | Experience Platform | No business, investment, accounting, or authorization meaning |
| User Preference State | A person's presentation or interaction preference | Experience Platform | No policy, decision, goal, or financial truth |
| Intent Reference | A proposed human action routed to the responsible domain gate | Experience owns capture and routing only | Not approval, instruction, execution, or recorded domain action |

The table defines responsibilities at architecture level. It does not prescribe
storage, identifiers, fields, wire representations, or lifecycle commands.

### 5.3 Cardinality rules

- A Product Workspace is one isolated product context.
- A Portfolio Identity belongs to exactly one workspace under the existing
  Portfolio Domain Model.
- A workspace may reference zero, one, or many Portfolio Identities.
- A Workspace Context may carry zero or one Current Selection.
- Any selected portfolio must belong to the active workspace.
- A Focus Reference is optional and may identify only an object available
  inside the active workspace context.
- A product concern may contribute through multiple attachment points. Each
  Product Contribution has one declared context requirement and an explicit
  mapping from every concept it uses to that concept's one canonical owner; the
  contribution itself is never a synthetic semantic owner.
- No default permits aggregation, selection, navigation, state, or intent to
  cross a workspace boundary.

## 6. Workspace responsibilities

### 6.1 The workspace is responsible for

- establishing and preserving the active isolation context;
- making applicable product scope explicit to every composition;
- carrying Current Selection and bounded focus without redefining either
  referenced object;
- composing product navigation from declared attachment contributions;
- exposing Product Contribution presence, absence, and degraded availability
  honestly;
- preserving orientation when a person moves between contributed surfaces;
- maintaining namespaced interaction and preference state;
- capturing proposed human intent and routing it to the owning constitutional
  gate;
- preventing an extension from reading or affecting context it did not
  declare; and
- retaining semantic owner, provenance, temporal meaning, and degraded-state
  information supplied with every domain projection.

### 6.2 The workspace is never responsible for

- defining Asset, Portfolio, Wealth, market, ledger, analytical, judgment,
  evaluation, execution, or authorization truth;
- calculating or correcting any domain-owned value;
- deciding whether a recommendation, transaction, configuration change, or
  execution action is valid;
- granting access, authority, ownership, independence, approval, or consent;
- turning a selected or visible object into an owned or authorized object;
- creating a cross-domain semantic aggregate that competes with its sources;
- treating a missing source as zero, current, safe, or approved; or
- making a Product Contribution mandatory merely because it occupies a navigation
  position.

## 7. Workspace context model

Workspace Context is the minimum logical frame needed to interpret a product
interaction without ambient assumptions.

| Context element | Required meaning | Rule |
| --- | --- | --- |
| Workspace reference | Which isolated product context applies | Always explicit |
| `ActorRef` | Which exact M33 actor applies, when an actor is relevant | Use the frozen namespaced actor and provider reference; never substitute a username, email, display name, token, current owner, or generic principal alias |
| Current Selection | Which portfolio is currently viewed, when applicable | Optional; must resolve inside the workspace |
| Focus Reference | Which domain object is currently in focus, when applicable | Optional; owner and object type remain explicit |
| Contribution reference | Which declared Product Contribution applies | Required for a contributed surface or action |
| Navigation position | Where the person is oriented in the product topology | Interaction state only |
| Provenance reference | Which source supplied a displayed domain projection | Required whenever the source contract requires it |
| Temporal context | The source-owned time meaning carried with a projection | Never replaced by a presentation label |
| Degraded-state context | Whether a source or contribution is incomplete, stale, unavailable, or otherwise qualified | Must remain visible and source-specific |
| M33 authority references | Which exact `AuthorizationScope`, `Permission`, `GrantSourceRef`, and point-in-time `ActorAuthorityFact` apply to a proposed action governed by M33 | Never inferred from selection, visibility, membership, navigation, or the other context elements |

Context has no business meaning by itself. Changing context changes what the
person is viewing or proposing, not the referenced financial state.

### 7.1 Context invariants

- Context resolution precedes Product Contribution composition.
- An unresolved workspace reference stops workspace composition.
- An unresolved Current Selection removes portfolio-scoped contributions; it
  does not select an arbitrary portfolio.
- A context mismatch is surfaced as a boundary error, never repaired by
  silent fallback.
- Deep entry into the product must reconstruct and validate the same explicit
  context as entry through top-level navigation.
- Context may be transferred between surfaces only through the canonical
  context contract; private extension state is not context.
- Authority is checked by the responsible authority boundary at the point of
  action. An `ActorAuthorityFact` remains a point-in-time M33 fact and is not
  cached as a semantic property of Workspace Context.

### 7.2 Frozen identity and authority binding

M35-WP1 consumes the frozen M33 contracts directly and creates no weaker
identity or authority abstraction:

- actor identity is an exact `ActorRef`;
- when authentication provenance is required, it is an exact
  `AuthenticationEventRef` plus the applicable current `ActorStatusFact`;
- an M33-governed action uses an exact `AuthorizationScope` containing the
  authority namespace, workspace id, and portfolio id, plus the exact
  applicable `Permission`;
- grant provenance is an exact `GrantSourceRef`;
- point-in-time authority is an exact `ActorAuthorityFact`; and
- where the identity-validation boundary is invoked, its governed
  `IdentityValidationPolicy`, `IdentityValidationInput`, and
  `IdentityValidationResult` remain intact.

The Context Envelope may carry references to those contracts so an interaction
can be interpreted, but it does not validate them or turn them into ambient
authority. The Intent Envelope carries the exact applicable references and
bindings to the owning gate. A display name, route, selected portfolio,
provider role, membership label, boolean permission, or current-session guess
cannot substitute for an M33 contract. Identity-provider selection and runtime
integration remain deferred; the architectural contract boundary does not.

## 8. Workspace state model

Workspace state is partitioned so interaction convenience can never become a
second source of domain truth.

| State class | Examples of meaning | Durability stance | Authority |
| --- | --- | --- | --- |
| Foundation state | Workspace Identity and boundary relationship | Stable operational reference | Experience Platform operational shell |
| Context state | Current Selection, Focus Reference, navigation position | Replaceable interaction state | Experience Platform |
| Preference state | Presentation and interaction choices | Retained only as user preference | Experience Platform |
| Contribution state | Extension-local Interaction State | Namespaced, removable with its contribution | Experience Platform owns the state and its meaning; the extension owns only its allocated namespace |
| Projection state | Read-only representation of source-owned information | Recomputable or refreshable; never promoted to truth | Original source domain |
| Proposed-intent state | Human input not yet accepted by an owning gate | Explicitly pending and non-authoritative | Experience captures; owner decides |
| Domain record | Ledger event, observation, analysis, judgment, evaluation, authorization, or other owned fact | Governed entirely by its source domain | Outside workspace ownership |

### 8.1 State transition rules

- Selecting, focusing, navigating, and personalizing may change only
  Experience-owned state.
- Attaching or detaching a Product Contribution may change composition, never
  source-domain records.
- Refreshing a projection may replace its representation only with another
  projection obtained under the source contract.
- Submitting proposed intent ends workspace ownership of the decision. The
  owning gate alone determines acceptance, rejection, or resulting record.
- Loss of an extension removes only its namespaced contribution state.
- An extension's ownership of a namespace never transfers ownership of the
  Interaction State stored under that namespace away from Experience Platform.
- Closing or leaving a workspace does not delete referenced portfolios,
  domain histories, or immutable records.
- No workspace-state transition constitutes authorization or execution.

## 9. Product navigation model

Navigation is a semantic orientation graph assembled from product attachment
points. It is not a fixed route tree and does not prescribe screens.

```text
Workspace Entry
  |
  +-- Workspace Scope
  |     orientation across contributions within the one active Workspace Context
  |
  +-- Portfolio Scope
  |     orientation within one Current Selection
  |
  +-- Object Focus
  |     inspection of one referenced domain object
  |
  +-- Contribution Focus
  |     orientation to a contribution preserving every concept's canonical owner
  |
  +-- Governed Product Operations
        context, preference, and externally authorized administration
```

These are attachment classes, not feature names. A future product concern
selects the narrowest lawful class; it does not create a new root merely
because it is important.

### 9.1 Navigation laws

1. The workspace is the product root after entry into an isolated context.
2. Product scope precedes contribution choice: workspace, then applicable
   portfolio or object context, then contribution.
3. Cross-portfolio composition remains inside one workspace and preserves the
   identity and owner of every underlying concept.
4. Portfolio-scoped contributions consume Current Selection explicitly.
5. Object-focused contributions carry a canonical object reference, never a
   display label as identity.
6. Navigation parents own relationships and orientation only; they do not own
   child semantics.
7. A contribution may appear in more than one navigation position only when
   each placement uses the same one active Workspace Context, the same
   concept-to-canonical-owner mapping, and its declared context requirements.
8. Availability and authorization remain separate. Hidden, visible,
   unavailable, and unauthorized are not interchangeable states.
9. Removing a contribution leaves the foundation topology valid.
10. Route paths, menu labels, tabs, responsive variants, and visual order are
    implementation or product-design decisions outside M35-WP1.

## 10. Logical workspace services

The following are logical responsibilities. They do not imply deployable
services, APIs, classes, processes, or storage units.

| Logical service | Responsibility | Explicit non-responsibility |
| --- | --- | --- |
| Workspace Directory | Resolve available Workspace Identities from an authoritative operational source | Does not establish identity authority, membership, or access policy |
| Context Resolver | Validate and assemble Workspace Context | Does not infer missing scope or authorization |
| Selection Coordinator | Maintain Current Selection inside the active workspace | Does not change Portfolio Identity or Accounting Scope |
| Navigation Composer | Assemble orientation from valid contributions | Does not own contribution semantics or permission decisions |
| Contribution Catalog | Describe available Product Contribution contracts and attachment points | Does not prove runtime health, authorization, or correctness |
| Projection Coordinator | Request and present source-owned projections with provenance and degradation intact | Does not calculate, merge authority, or correct source data |
| Interaction State Coordinator | Maintain bounded context, preference, and namespaced contribution state | Does not persist domain truth or policy |
| Intent Router | Deliver proposed human intent to the responsible constitutional gate | Does not validate, approve, authorize, or execute it |
| Extension Governor | Validate contribution declarations against workspace contracts | Does not create plugin semantics, domain authority, or implementation permission |
| Degradation Coordinator | Surface unavailable or qualified contributions without silent substitution | Does not convert unknown or stale state into a valid value |

An implementation may combine or separate these responsibilities freely so
long as their contracts and ownership boundaries remain intact.

## 11. Canonical product contracts

These contracts specify required meanings and invariants, not serialized
fields or APIs.

### 11.1 Workspace Descriptor

Identifies one Product Workspace and its isolation boundary. It may reference
externally governed availability and an exact M33 `ActorRef` when an actor is
relevant. It never contains a financial balance, portfolio truth, permission
grant, or implied authority.

### 11.2 Context Envelope

Carries the explicit Workspace Context required to interpret a contribution or
proposed intent. It distinguishes absent, unresolved, and inapplicable values.
When actor or authority context is applicable it uses the frozen M33 contracts
listed in section 7.2. It never converts a display label into `ActorRef`, a
generic role into `Permission`, or an authority reference into authority
itself.

### 11.3 Scope Reference

References the applicable workspace, Portfolio Identity, Accounting Scope, or
domain object without redefining it. A reference must preserve the canonical
identifier and canonical owner of the referenced concept. It does not replace
M33 `AuthorizationScope` where authority scope is required.

### 11.4 Product Contribution Descriptor

Declares a Product Contribution's identity, purpose boundary, context
requirements, attachment classes, read dependencies, proposed-intent types,
degraded modes, foundation compatibility, and the canonical owner of every
concept it uses. Experience owns this descriptor grammar and the catalogued
composition relationship. The descriptor creates no semantic owner for the
contribution as a whole. Presence in the catalog is not evidence that the
contribution is implemented, healthy, authorized, or enabled.

### 11.5 Navigation Contribution

Declares where a Product Contribution may attach, which context it requires, which
orientation relationship it adds, and how its absence is represented. It
owns no displayed business concept.

### 11.6 Projection Contract

Requires every displayed domain projection to preserve semantic owner,
canonical identifiers, provenance, temporal meaning, confidence or quality
where applicable, and explicit degradation. Composition may align
projections; it may not manufacture a new authoritative aggregate.

### 11.7 Intent Envelope

Carries a person's proposed action, explicit context, referenced objects,
provenance of capture, and target authority boundary. For an action governed
by M33, it carries the exact applicable `ActorRef`,
`AuthenticationEventRef`, `ActorStatusFact`, `AuthorizationScope`,
`Permission`, `GrantSourceRef`, `ActorAuthorityFact`, and validation binding
required by that boundary; it does not replace them with M35 fields. Before
acceptance by the owning gate it remains proposed intent only. The envelope
grants no approval, execution, implementation, or runtime authority.

### 11.8 Interaction State Contract

Confines interaction and preference state to Experience-owned meaning. Each
extension owns only its allocated namespace and declares whether state is
temporary, retained, or discardable. Experience Platform remains the owner of
the Interaction State and its meaning. The contract cannot store a shadow copy
of domain truth.

### 11.9 Extension Manifest

Aggregates the Product Contribution Descriptor, navigation contributions, context
requirements, state namespace, dependency declarations, degradation behavior,
concept-to-canonical-owner mapping, and foundation compatibility claim for one
extension. It is an architecture declaration, not a packaging format or
installation mechanism.

## 12. Ownership boundaries

| Concern | Canonical owner | Workspace relationship |
| --- | --- | --- |
| Workspace identity, isolation, navigation, interaction, and composition | Experience Platform operational shell | Owns the product-context concern |
| Portfolio Identity and Accounting Scope | Ledger & Accounting | References only; never redefines |
| Portfolio Strategy Metadata and portfolio-derived knowledge | Portfolio Intelligence | Presents source-owned projections |
| Goal Target and whole-financial-picture meaning | Wealth Intelligence | Presents source-owned projections |
| Asset identity and classification | Asset Foundation | Uses canonical references only |
| Market observations | Market Intelligence | Preserves provenance, time, and degradation |
| Investment judgment and decision policy | Decision Intelligence | Presents judgment and routes proposed intent only |
| Evaluation | Trust & Evaluation | Presents observer outputs without operational dependency |
| Ingestion and normalization | Connectivity & Ingestion | Does not bypass the ingestion gate |
| Human identity and authentication | Managed identity provider under frozen M33.9 | Uses exact M33 `ActorRef`, authentication-event, and actor-status contracts; never substitutes an M35 identity abstraction |
| Workspace membership, portfolio grants, authorization policy, resource status, and point-in-time authority | Application-owned Identity and Authorization domain under frozen M33.9 | Uses exact M33 scope, permission, grant-source, authority-fact, and validation contracts; never infers authority from workspace context |
| Implementation and runtime authority | Existing authorization process | Always external to M35-WP1 |

### 12.1 Cross-domain composition rule

A product composition is a set of references and projections, not a new
semantic owner. Each constituent retains:

- its canonical name and identifier;
- its constitutional owner;
- its source and provenance;
- its temporal and degraded-state meaning;
- its authorization boundary; and
- its independent lifecycle.

If a composition requires a new business concept, that concept must be
governed by the existing architecture process before any workspace attachment
may rely on it.

## 13. Extension architecture

### 13.1 Extension rule

A workspace extension is a bounded product contribution attached by
declaration. It is not necessarily a plugin implementation, deployment unit,
package, screen, or service.

Every extension must declare:

- one stable contribution identity and one immutable Extension Manifest
  revision; a changed declaration creates an explicit successor revision and
  never rewrites the prior declaration;
- the one canonical owner of each concept it uses, without assigning a
  semantic owner to the contribution as a whole;
- its purpose and explicit non-purpose;
- required workspace, portfolio, object, or authority context;
- its permitted navigation attachment classes;
- read-only projection dependencies;
- any proposed-intent types and their target gates;
- its owned interaction-state namespace, while Experience retains ownership
  of Interaction State and its meaning;
- unavailable, stale, partial, and incompatible behavior;
- compatibility with the exact approved foundation contract identity and
  revision defined in section 13.3; and
- removal behavior that leaves source-domain records untouched.

### 13.2 Extension prohibitions

An extension may not:

- create a new product root outside Workspace Context;
- redefine a canonical concept or claim ownership through composition;
- read ambient selection, identity, or authority state;
- write source-domain truth outside an existing constitutional gate;
- treat visibility, installation, enablement, or selection as authorization;
- create a second implementation of an owned business rule;
- require another extension's private state;
- hide or weaken source degradation;
- make foundation navigation invalid when absent; or
- require a foundation redesign to add an ordinary Product Contribution.

### 13.3 Compatibility posture

The architecture-level foundation contract identity is `M35-WP1`. A
compatibility claim binds one stable contribution identity and one immutable
Extension Manifest revision to that foundation identity. Before this proposal
is approved, no extension may claim compatibility with it. After approval, the
claim also identifies the exact immutable approved foundation repository
revision. An absent, unknown, or incompatible identity or revision does not
attach.

Foundation contracts evolve additively. A new optional context element or
attachment class may be declared compatible without invalidating existing
contributions. A change that weakens an invariant, changes an ownership
boundary, or changes the meaning of an existing contract is incompatible and
requires architectural review at the level that owns that rule. Supersession
must name the prior immutable revision and the successor revision explicitly;
it never rewrites an earlier compatibility claim.

This is the complete identity, revision, and compatibility rule required by
M35-WP1. Release versioning, serialization, version-range syntax, negotiation,
packaging, installation, distribution, and runtime enforcement remain
deferred.

## 14. Future product-concern attachment strategy

The table identifies only where a future product concern can attach. It does
not define or authorize that concern.

| Future concern | Attachment point | Foundation dependency | Deferred decision |
| --- | --- | --- | --- |
| Multiple portfolios | Workspace Scope and Portfolio Scope | Explicit set of Portfolio Identity references and optional Current Selection | Aggregation semantics and product behavior |
| Multiple asset classes | Object Focus and source projections | Canonical Asset identity and capability descriptions | Asset definitions, valuation, and lifecycle behavior |
| AI | Contribution Focus and Intent Router | Source-owned evidence projection and explicit proposed intent | Models, prompts, autonomy, recommendations, and evaluation |
| Execution | Intent Router to the existing decision gate | Explicit context and separately valid authority | Planning, approval, broker, venue, and runtime behavior |
| Plugins | Extension Manifest and governed attachment classes | Namespaced state, declared ownership, compatibility, degradation | Packaging, installation, trust, and distribution |
| Personalization | Interaction State Contract | Experience-owned preference namespace | Preference catalog and behavior |
| Dashboards | Workspace Scope, Portfolio Scope, or Contribution Focus composition | Projection contracts and navigation contribution | Metrics, layout, visualization, and prioritization |
| Team or shared use | Workspace Context `ActorRef` | Frozen M33 identity, membership, scope, permission, and authority contracts | RBAC behavior, collaboration, tenancy behavior, audit behavior, and delegation policy |
| Notifications or realtime | Product Contribution with degradation contract | Explicit context and source-owned temporal semantics | Delivery, subscription, urgency, transport, and runtime |

The foundation succeeds only if these concerns can be added through their
attachment contracts without changing Workspace Identity, Workspace Context,
the state partition, navigation laws, or ownership boundaries.

## 15. Architectural decision register

These are M35-WP1 design decisions. They do not amend higher-level governance
and do not constitute standalone ADR approval.

| Decision | Ruling | Reason |
| --- | --- | --- |
| `M35-WP1-A01` | Product Workspace is an Experience Platform operating context, not a tenth platform domain | Preserves the constitutional domain model and M34 one-concept/one-owner rulings |
| `M35-WP1-A02` | Workspace is an isolation and composition boundary, not an accounting, authorization, or semantic boundary | Prevents context from acquiring domain truth or authority |
| `M35-WP1-A03` | Context is explicit and portable through the proposed canonical Context Envelope | Eliminates route-, cache-, and extension-specific ambient scope |
| `M35-WP1-A04` | Navigation is an attachment graph over semantic context, not a fixed route hierarchy | Allows implementation and product design to evolve without moving ownership |
| `M35-WP1-A05` | Workspace services are logical responsibilities, not deployable components | Preserves technology independence |
| `M35-WP1-A06` | Extensions attach by declaration and own only their allocated namespace; Experience owns the Interaction State and its meaning | Supports plugins and future product concerns without foundation surgery or state-ownership transfer |
| `M35-WP1-A07` | All domain writes leave the workspace through an existing constitutional gate | Preserves truth, intent, and authority boundaries |
| `M35-WP1-A08` | One foundation serves one or many workspaces, portfolios, assets, M33 actors, and Product Contributions | Avoids cardinality-driven redesign without introducing a generic identity abstraction |

## 16. Foundation invariants

The foundation is conformant only while all of these remain true:

1. Every interaction has one explicit Workspace Context.
2. No workspace aggregates across another workspace by default.
3. Every portfolio-scoped contribution uses an explicit Current Selection or
   explicit Portfolio Identity.
4. Current Selection never changes Portfolio Identity or Accounting Scope.
5. Every domain projection retains its source owner and provenance.
6. No Experience composition computes or corrects a domain-owned number.
7. No navigation relationship grants authority or transfers semantic
   ownership.
8. Every proposed action is routed to the gate owned by the affected domain.
9. Every extension is removable without changing domain truth or foundation
   validity.
10. Every extension owns only its namespace; Experience owns its namespaced
    Interaction State, which remains non-authoritative.
11. Missing, stale, partial, incompatible, and unauthorized remain distinct
    and visible.
12. Implementation and runtime authority remain external to the workspace.

## 17. Explicit deferrals

M35-WP1 intentionally does not determine:

- how workspaces are created, archived, transferred, recovered, or deleted;
- who may join, administer, or act within a workspace;
- whether a person may belong to multiple workspaces;
- how the frozen M33 identity and authority contracts are implemented,
  persisted, transported, or integrated with an identity provider; their
  architectural representation and ownership are not deferred;
- which product areas, routes, screens, labels, or dashboards exist;
- which Product Contributions are mandatory, optional, installed, or enabled;
- how extension trust, distribution, compatibility negotiation, packaging, or
  installation works; the architecture-level compatibility declaration in
  section 13.3 is not deferred;
- how context or state is persisted, synchronized, cached, or transported;
- any calculation, analytical, recommendation, execution, AI, notification,
  realtime, pricing, or Asset Registry design; or
- any implementation milestone, technology selection, or runtime rollout.

Each deferral belongs to a later product or implementation decision. None
is silently answered by this foundation.

## 18. Review and completion criteria

M35-WP1 may be accepted as the Product Workspace Foundation only if an
architectural review confirms that:

- all requested foundation concerns are covered by one coherent model;
- the model creates no new constitutional domain or business-truth owner;
- M34 ownership, vocabulary, admission, and authorization decisions remain
  unchanged;
- multi-workspace, multi-portfolio, multi-asset, AI, execution, plugin,
  personalization, and dashboard futures attach without foundation redesign;
- every future product concern remains behaviorally unspecified;
- contracts are technology- and implementation-independent;
- explicit context replaces ambient scope;
- navigation and visibility remain separate from authority;
- no runtime, implementation, or governance authority is claimed; and
- all links and constitutional references resolve.

## 19. Retained non-authorizations

This document creates no:

- implementation plan, implementation authority, or source-code change;
- runtime plan, runtime authority, or deployment change;
- product feature, UI design, route, API, schema, or infrastructure;
- financial, analytical, recommendation, execution, AI, or evaluation
  behavior;
- workspace membership, role, access, delegation, or authorization rule;
- authorization record, evidence acceptance, gate outcome, or approval;
- change to any frozen M34 artifact or earlier milestone; or
- amendment to the Platform Architecture, canonical vocabulary, or existing
  architectural decisions.

Retained state:

```text
M29-M34:                 CLOSED AND FROZEN
M35-WP1 architecture:    PROPOSED_FOR_SECOND_ARCHITECTURAL_REVIEW
Product implementation: NOT AUTHORIZED
Runtime adoption:        NOT AUTHORIZED
Implementation authority: NONE
Runtime authority:        NONE
```

The next lawful action is a second independent architectural review of this
revised M35-WP1 foundation and its M35-WP2 remediation trace. No
product-concern design or implementation follows by implication.
