# M36 - Multiple Portfolio Foundation Epic Closeout

**Closeout date:** 2026-07-20

**Decision:** **M36 is closed and canonical.** M36-WP1 is approved, both
independent-review findings are resolved, and Portfolio Lifecycle State is
registered in the canonical Glossary. Implementation authority and runtime
authority remain `NONE`.

## 1. Milestone purpose

M36 established the technology-independent foundation through which one M33
actor may own or work with zero, one, or many portfolios inside one Product
Workspace. It preserves the existing separation among Portfolio Identity,
Accounting Scope, Portfolio Lifecycle State, Current Selection, workspace
composition, source availability, and point-in-time authority.

M36 is architecture only. It creates no product behavior, persistence,
interface, authorization implementation, or runtime adoption.

## 2. Governing inputs

M36 remains subordinate to and consistent with:

- [Platform Architecture](../architecture/platform_architecture.md), including
  domain ownership, downward dependencies, gates, Experience non-ownership,
  and vocabulary governance;
- [Portfolio Domain Model](../architecture/PORTFOLIO_DOMAIN_MODEL.md),
  especially sections 3, 8, and 9;
- [Canonical Glossary](../GLOSSARY.md);
- [M33.8 stable human identity and scoped authorization
  foundation](M33_8_stable_human_identity_and_scoped_authorization_foundation.md);
- [M33.9 identity and authorization ownership
  decision](M33_9_identity_authority_provider_selection_and_integration_feasibility.md);
- [M34 Decision Register](m34/audit/registers/decision_register.md), especially
  `M34-D-0002`, `M34-D-0003`, `M34-D-0007`, `M34-D-0009`, and
  `M34-D-0010`; and
- the frozen [M35 Product Workspace
  Foundation](M35_WP1_Product_Workspace_Foundation.md).

## 3. Final architecture delivered

The canonical [M36-WP1 Multiple Portfolio
Foundation](M36_WP1_Multiple_Portfolio_Foundation.md) establishes:

- one Product Workspace referencing zero or more exact Portfolio Identities;
- one Workspace Context carrying zero or one Current Selection;
- one separate Ledger-owned Accounting Scope for every Portfolio Identity;
- exact portfolio referenceability through Portfolio Identity, its one-
  workspace relationship, and the M35 Context Resolver applying Scope
  Reference;
- explicit context propagation and fail-closed mismatch behavior;
- separation of referenceability, source availability, lifecycle state,
  selection, authority, and governed-action eligibility;
- navigation and selection as Experience-owned orientation only;
- ownership-preserving multi-portfolio composition;
- lifecycle and future Product Contribution attachment points; and
- technology-independent invariants and deferrals.

## 4. Architectural decisions

M36-WP1 records `M36-WP1-A01` through `M36-WP1-A10`. Together they establish
that:

- Active Portfolio is not a canonical concept;
- Portfolio Lifecycle State and Current Selection remain separate;
- workspace/portfolio cardinalities preserve M35 and the Portfolio Domain
  Model;
- Current Selection has no architecture default and grants no authority;
- identity, relationship, resolution, availability, lifecycle, selection, and
  authority remain independent concerns;
- M33 applies only where an existing governed action boundary invokes it;
- multi-portfolio composition creates no aggregate business truth; and
- future concerns attach only through frozen M35 contracts with declared
  portfolio-context requirements.

## 5. Independent review and remediation

The first independent architectural review returned `CHANGES REQUIRED` with
two findings:

| Finding | Original classification | Required correction | Final disposition |
| --- | --- | --- | --- |
| `M36-ARB-F01` | `BLOCKER` | Define and own the lifecycle state without colliding with Portfolio Status | `RESOLVED` |
| `M36-ARB-F02` | `MAJOR` | Separate referenceability, source availability, Current Selection, and M33 action authority | `RESOLVED` |

The [M36-WP2 Architectural Remediation
Summary](M36_WP2_Architectural_Remediation_Summary.md) records the bounded
corrections and preserves the first-review history. The second independent
architectural review returned `APPROVED` and confirmed both findings resolved,
subject to same-change registration of Portfolio Lifecycle State.

## 6. Canonical Glossary registration

The approval change registers **Portfolio Lifecycle State** in the canonical
Glossary as the recorded `active`, `archived`, or `closed` lifecycle state of
one Portfolio Identity, owned by Ledger & Accounting.

The registered term is explicitly not Portfolio Status, Current Selection,
source availability, authority, permission, action eligibility, or transition
legitimacy. The existing Portfolio Status definition and Portfolio
Intelligence ownership remain unchanged. Registration satisfies Platform
Architecture vocabulary governance and completes the second-review condition.

## 7. Retained ownership boundaries

- Ledger & Accounting continues to own Portfolio Identity, Accounting Scope,
  Portfolio Membership, ledger history, and Portfolio Lifecycle State.
- Portfolio Intelligence continues to own Portfolio Strategy Metadata and
  Portfolio Status.
- Experience Platform continues to own Workspace Context, Current Selection,
  navigation, and composition as interaction concerns only.
- The M33 Identity and Authorization boundary continues to own actor identity,
  grants, policy, resource status, and exact point-in-time authority facts.
- Wealth Intelligence continues to own whole-wealth aggregation and meaning.
- Product Contributions retain every constituent concept's canonical owner and
  create no synthetic semantic owner.
- Navigation, visibility, availability, selection, and lifecycle state create
  no authority.

## 8. Explicit deferrals

M36 leaves deferred:

- persistence, schemas, APIs, events, transport, caching, synchronization,
  frontend, backend, infrastructure, and deployment;
- authentication and authorization implementation;
- generic read-access or portfolio-view policy;
- workspace membership, grants, inheritance, delegation, sharing, and RBAC;
- portfolio lifecycle commands, workflows, and runtime eligibility rules;
- selection retention, defaults, ordering, grouping, favorites, recents, and
  search behavior;
- comparison, aggregation, analytics, wealth, dashboards, notifications, AI,
  trading, execution, and transfers; and
- Product Contribution enablement, plugin runtime, and all runtime adoption.

These deferrals do not weaken the canonical M36 boundaries and authorize no
future behavior.

## 9. Authority state

```text
M29-M35:                  CLOSED AND FROZEN
M36:                      CLOSED AND CANONICAL
M36-WP1:                  APPROVED
M36-WP2:                  COMPLETE
Portfolio Lifecycle State: REGISTERED IN CANONICAL GLOSSARY
Implementation authority: NONE
Runtime authority:         NONE
```

M36 creates no implementation plan, source-code change, data migration,
runtime plan, deployment, product enablement, or authorization to begin any
deferred capability.

## 10. Exact reopen triggers

M36 may reopen only when a proposed architectural change would alter at least
one canonical M36 foundation rule:

1. change Product Workspace-to-Portfolio cardinality or allow a Portfolio
   Identity to belong to more than one workspace;
2. make Current Selection multi-valued, implicit, authoritative, or owned
   outside Experience Platform;
3. add, remove, rename, or change the meaning or owner of a Portfolio Lifecycle
   State;
4. change Portfolio Identity, Accounting Scope, or lifecycle-history survival
   across transitions;
5. make referenceability depend on generic authority, availability, UI state,
   or an inferred portfolio reference;
6. permit navigation, visibility, availability, selection, or lifecycle state
   to grant or imply authority;
7. introduce cross-workspace composition by default or a cross-portfolio
   aggregate that lacks an existing canonical owner;
8. change M33 exact-scope authority contracts in a way that changes M36's
   governed-action boundary; or
9. require a future Product Contribution to violate M35/M36 context,
   ownership, degradation, or attachment invariants.

Implementation choices that conform to M36, and capabilities attaching through
its existing contracts, do not reopen M36.

## 11. Recommended next milestone

The recommended next architecture milestone is **M37 - Universal Asset Search
Foundation**.

This recommendation identifies an architectural direction only. It does not
authorize M37 implementation, runtime adoption, source-code changes, schemas,
APIs, interfaces, infrastructure, or deployment.
