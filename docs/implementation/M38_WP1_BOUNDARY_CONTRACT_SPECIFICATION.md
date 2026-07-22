# M38-WP1 — Boundary Contracts and Conformance Specification

**Status:** Approved and frozen  
**Milestone:** M38 — Product Workspace Foundation  
**Document role:** Canonical technical specification  
**Normative language:** **MUST**, **MUST NOT**, and **MAY** are normative.

## 1. Executive summary

This document freezes the contracts through which the Experience Platform
composes a provider-neutral Product Workspace.

The following boundaries are load-bearing:

- `workspace_id` identifies the Experience-owned Product Workspace context.
- `asset_id` is the only canonical identity permitted for Asset Focus.
- Universal Search is consumed only through its frozen M37 public contract.
- Workspace composition transfers no semantic ownership; every displayed fact
  remains owned by its source domain.
- A Discovery Candidate MAY open a transient Discovery Experience, but MUST
  NOT establish Asset Focus, create a durable route, or become workspace
  identity.
- Future Resolver, projection, Intelligence, and intent capabilities attach
  only through reserved seams.

M35, M36, and M37 remain frozen. This specification does not amend them.

### 1.1 Constitutional clarification

The phrase “Intelligence consumes workspace” means that Experience MAY invoke
Intelligence using explicit lower-domain scope references and compose the
returned projection. It MUST NOT mean that an Intelligence domain imports or
depends on the Experience-owned `ProductWorkspaceContext`; that dependency
would contradict the platform dependency law.

## 2. Scope and terminology

This specification defines runtime contracts, ownership, state machines,
dependency rules, conformance requirements, and the WP1 acceptance gate. It
does not define implementation language, framework types, persistence schema,
or concrete future-domain behavior.

“Source domain” means the domain that owns a fact’s meaning. “Composition”
means carrying or presenting references and projections without changing their
meaning. “Reserved” means declared but unbound and unavailable in M38.

## 3. Canonical runtime contracts

### 3.1 ProductWorkspaceContext

**Purpose.** The explicit Experience-owned runtime frame within which one
product interaction is interpreted.

**Canonical owner.** Experience Platform.

| Field | Presence | Meaning | Owner |
|---|---|---|---|
| `workspace` | Conditional | Required for `RESOLVED` and `DISCARDED`; a `REJECTED` descriptor MAY be present for `REJECTED`; absent for `UNRESOLVED` | Experience Platform |
| `current_selection` | Optional | Zero-or-one selection relationship to a Portfolio Identity | Experience Platform |
| `current_selection.portfolio_id` | Conditional | Referenced Portfolio Identity | Portfolio / Ledger & Accounting |
| `asset_focus` | Optional | Current `AssetFocusReference` | Experience Platform |
| `active_contribution_id` | Optional | Contribution providing the active surface | Experience Platform |
| `navigation_position` | Optional | Non-authoritative product orientation | Experience Platform |
| `context_state` | Required | `UNRESOLVED`, `RESOLVED`, `REJECTED`, or `DISCARDED` | Experience Platform |

M38 does not add actor, permission, grant, or authority fields. A future action
contract MUST reuse the exact frozen M33 contracts.

**Lifecycle.** Resolve the workspace; attach optional selection, focus,
contribution, and navigation state; replace or discard the context as the
interaction changes.

**Invariants.** A `RESOLVED` context contains exactly one resolved Workspace
Identity; context is explicit; Current Selection is zero-or-one and MAY be
`NONE`; Asset Focus, when present, contains one Registry-issued `asset_id`;
navigation is not authority; context resolution precedes composition;
`UNRESOLVED`, `REJECTED`, and `DISCARDED` contexts MUST NOT compose.

**Allowed transitions.** `UNRESOLVED` → `RESOLVED`; `UNRESOLVED` →
`REJECTED`; `RESOLVED` → `DISCARDED`. Selection may be set, cleared, or
replaced while `RESOLVED`; focus may be requested, activated, cleared, or
replaced while `RESOLVED`; navigation may change while `RESOLVED`.

`REJECTED` and `DISCARDED` are terminal for that context instance. A retry or
new interaction creates a new context instance.

**Prohibited states.** Multiple workspaces, multiple selections, an inferred
default portfolio, symbol/provider/claim-based focus, unvalidated focus,
authority inferred from context, or silent workspace switching.

### 3.2 WorkspaceDescriptor

**Purpose.** Identifies one Product Workspace and its Experience-owned
isolation boundary.

**Canonical owner.** Experience Platform operational shell.

| Field | Presence | Meaning | Owner |
|---|---|---|---|
| `workspace_id` | Required | Stable Workspace Identity | Experience Platform |
| `display_label` | Optional | Presentation label only | Experience Platform |
| `descriptor_state` | Required | `RESOLVED`, `UNAVAILABLE`, or `REJECTED` | Experience Platform |

The descriptor MUST NOT contain portfolio lists, defaults, membership,
permissions, RBAC, tenancy, or authority.

**Lifecycle.** A `RESOLVED` descriptor is established by the operational
shell, returned by current-context bootstrap, referenced by navigation, and
replaced only by a future authorized workspace-context change. A descriptor
may subsequently become `UNAVAILABLE`. A rejected lookup may produce a
`REJECTED` descriptor; an unresolved reference is not a descriptor state.

**Invariants.** `workspace_id` is stable and opaque; `display_label` is never
used for equality or routing; M38 exposes only the current runtime workspace.

**Allowed transitions.** `RESOLVED` → `UNAVAILABLE` when the runtime
workspace is no longer available. `REJECTED` and `UNAVAILABLE` are terminal for
that descriptor instance. Resolution from an unresolved reference is owned by
the Workspace Context state machine in §5.4 and does not add an unresolved
state to this contract.

**Prohibited states.** Missing identity, identity substituted by portfolio or
actor identifiers, multiple current descriptors, directory enumeration, or
access inferred from descriptor presence.

### 3.3 AssetFocusReference

**Purpose.** Represents the canonical asset currently in view without
transferring Asset identity ownership to Experience.

**Canonical owner.** Experience Platform owns the focus relationship and its
lifecycle. Registry / Asset Foundation exclusively owns the referenced
`asset_id` and all canonical Asset facts.

| Field | Presence | Meaning | Owner |
|---|---|---|---|
| `focus_kind` | Required | Asset discriminator | Experience Platform |
| `asset_id` | Required | Registry-issued canonical Asset Identity | Registry |
| `focus_state` | Required | `REQUESTED`, `ACTIVE`, or `REJECTED` | Experience Platform |

**Lifecycle.** Registered candidate or explicit deep link → requested → exact
Registry lookup → active or rejected; active focus MAY be cleared or replaced.

**Invariants.** `asset_id` is the only identity-bearing field; identity is
platform-global; a route is not proof of existence; Registry lifecycle does not
change identity; successor relationships do not silently replace focus.

**Allowed transitions.** A focus request creates `REQUESTED`; `REQUESTED` →
`ACTIVE` only after a successful exact Registry read; `REQUESTED` →
`REJECTED` after an unknown, unavailable, or invalid exact read. An `ACTIVE`
focus may be cleared or replaced; replacement creates a new `REQUESTED` focus
instance. `REJECTED` is terminal for that focus request.

**Prohibited states.** Focus from a Discovery Candidate, symbol or provider
fallback, pre-Registry activation, automatic successor substitution, or
provider validation.

### 3.4 DiscoveryExperienceContext

**Purpose.** A transient, provider-neutral Experience surface for inspecting a
Discovery Candidate without representing it as an Asset Workspace.

**Canonical owner.** Experience Platform.

| Field | Presence | Meaning | Owner |
|---|---|---|---|
| `workspace_id` | Required | Workspace in which interaction occurred | Experience Platform |
| `candidate` | Required | Unmodified M37 Discovery Candidate | Universal Search |
| `search_degradation` | Conditional | M37 degradation disclosure | Universal Search |
| `experience_state` | Required | `OPEN` or `CLOSED` | Experience Platform |

**Lifecycle.** Candidate selected → Open; close, replacement, or expiry →
Closed. Resolver handoff is outside M38.

**Invariants.** No Asset Focus, canonical identity, durable route, persistence,
domain record, or direct provider call exists. `claim_id` remains transient;
provider identity is provenance only; Search degradation remains visible.

**Allowed transitions.** Candidate selection creates `OPEN`; `OPEN` →
`CLOSED` on close, replacement, or expiry. `CLOSED` is terminal for that
Discovery Experience instance. Reopening creates a new instance.

**Prohibited states.** Discovery-to-Asset-Focus transition, durable claim
storage, client-side registration, portfolio mutation, or provider-specific
workspace behavior.

### 3.5 ProjectionEnvelope

**Purpose.** Carries a read-only source projection while preserving identity,
semantic ownership, provenance, temporal meaning, quality, and degradation.

**Canonical owner.** Experience Platform owns the envelope grammar and
composition mechanics; the declared source domain owns every enclosed fact.

| Field | Presence | Meaning | Owner |
|---|---|---|---|
| `projection_kind` | Required | Projection contract identity | Experience Platform |
| `subject_reference` | Required | Canonical subject identity | The single subject-identity owner named by the projection contract |
| `semantic_owner` | Required | Domain owning payload meaning | Declared source domain |
| `payload` | Conditional | Read-only source projection | Declared source domain |
| `provenance` | Conditional/required by source contract | Evidence lineage | Declared source domain |
| `temporal_context` | Conditional/required by source contract | Source-defined time meaning | Declared source domain |
| `quality_context` | Conditional/required by source contract | Confidence or completeness | Declared source domain |
| `degradation` | Conditional | Source qualification or failure | Declared source domain |
| `availability` | Required | `REQUESTED`, `AVAILABLE`, `DEGRADED`, `UNAVAILABLE`, `UNSUPPORTED`, or `DETACHED` | Experience Platform |

**Lifecycle.** Requested → available, degraded, unavailable, or unsupported;
refresh replaces the representation; detachment discards it without changing
source state.

**Invariants.** Payloads have a canonical subject and semantic owner; source
metadata is not rewritten; missing data is never treated as zero, current,
safe, or approved; composition never creates authoritative aggregates.
For each instantiated envelope, the projection contract MUST name exactly one
canonical owner for `subject_reference`; for example, Registry owns an
`asset_id` subject and Portfolio / Ledger & Accounting owns a `portfolio_id`
subject.

**Allowed transitions.** `REQUESTED` → `AVAILABLE`, `DEGRADED`,
`UNAVAILABLE`, or `UNSUPPORTED`; `AVAILABLE`, `DEGRADED`, or `UNAVAILABLE` →
`REQUESTED` on refresh; any non-detached state → `DETACHED` when the
attachment is removed. `UNSUPPORTED` is terminal for that request.
`DETACHED` is terminal for that envelope instance.

**Prohibited states.** Payload without ownership or subject, fabricated
provenance/time, silent stale substitution, Experience-computed domain facts,
or projection failure blocking unrelated workspace content.

### 3.6 ContributionDescriptor

**Purpose.** Declares how a Product Contribution attaches and identifies the
canonical owner of every concept it consumes.

**Canonical owner.** Experience Platform owns descriptor grammar, identity, and
composition; the descriptor creates no semantic owner for business content.

| Field | Presence | Meaning | Owner |
|---|---|---|---|
| `contribution_id` | Required | Stable, namespaced contribution identity | Experience Platform |
| `descriptor_revision` | Required | Revision of this descriptor | Experience Platform |
| `purpose_boundary` | Required | Declared product purpose and excluded behavior | Experience Platform |
| `attachment_classes` | Required | M35 attachment classes used by the contribution | Experience Platform |
| `context_requirements` | Required | Explicit Workspace Context inputs required for composition | Experience Platform |
| `read_dependencies` | Required | Public read contracts consumed by the contribution | Experience Platform |
| `projection_contracts` | Optional | Declared `ProjectionEnvelope` contracts | Experience Platform |
| `concept_owner_map` | Required | Maps every consumed concept to exactly one source owner | Experience Platform (declares source owners) |
| `declared_degraded_modes` | Required | Supported visible degradation behaviors | Experience Platform |
| `compatibility_claim` | Required | Product Workspace Foundation revision compatibility | Experience Platform |
| `reserved_slots` | Optional | `ReservedContributionSlot` attachments | Experience Platform |
| `intent_seam` | Optional | `IntentAttachmentSeam` declaration | Experience Platform |

**Lifecycle.** Declared → validated → available for composition → composed or
unavailable → superseded by a compatible revision.

**Invariants.** Every concept has exactly one owner; every dependency is
declared and public; catalog presence does not imply health, implementation,
enablement, or authority; state is namespaced; M38 future capabilities remain
unbound seams.

**Allowed transitions.** `DECLARED` → `VALIDATED`; `VALIDATED` →
`AVAILABLE_FOR_COMPOSITION` or `UNAVAILABLE`; `AVAILABLE_FOR_COMPOSITION` →
`COMPOSED` or `UNAVAILABLE`; any declared revision → `SUPERSEDED` when a
compatible replacement is accepted. `SUPERSEDED` is terminal for that
descriptor revision.

**Prohibited states.** Missing owner mapping, undeclared access, synthetic
ownership, undocumented ambient state, or a contribution becoming a second
product root.

### 3.7 ContributionAvailability

**Purpose.** Describes whether Experience can compose a declared contribution
attachment. It is not source-domain truth.

**Canonical owner.** Experience Platform.

| State | Meaning |
|---|---|
| `AVAILABLE` | Required composition contracts and projections are usable |
| `DEGRADED` | Usable, but optional capability or projection is qualified |
| `UNAVAILABLE` | Known and supported, but not currently composable |
| `UNSUPPORTED` | Required capability or implementation does not exist |
| `ABSENT` | No contribution is attached |

| Field | Presence | Meaning | Owner |
|---|---|---|---|
| `state` | Required | Exactly one availability state above | Experience Platform |
| `reason_code` | Required except for `AVAILABLE` | Experience reason for the composition state | Experience Platform |
| `source_degradation_refs` | Conditional | References applicable source-owned degradation records without rewriting them | Experience Platform owns the references; each referenced degradation record remains source-owned |
| `retry_allowed` | Required | Whether Experience may re-evaluate the attachment without a capability change | Experience Platform |
| `user_visible` | Required | Whether the availability condition is rendered to the user | Experience Platform |

**Invariants.** States are distinct; degraded and unavailable conditions are
visible; unsupported is not treated as a transient incident; absent is not a
failure.

**Lifecycle.** Evaluation produces one of the five availability states.
Re-evaluation may replace that state without mutating source-domain truth.
Detachment produces `ABSENT`.

**Allowed transitions.** `ABSENT` → `AVAILABLE`, `DEGRADED`, `UNAVAILABLE`,
or `UNSUPPORTED` when attachment is evaluated; `AVAILABLE`, `DEGRADED`, and
`UNAVAILABLE` may transition among one another on re-evaluation; any attached
state → `ABSENT` on detachment; `UNSUPPORTED` → `AVAILABLE`, `DEGRADED`,
or `UNAVAILABLE` only after the required capability or implementation changes.
No state is globally terminal because later attachment or capability changes
may require a new availability evaluation; `ABSENT` ends the detached
attachment instance.

**Prohibited states.** Simultaneous availability states, an unreasoned
non-`AVAILABLE` state, source-domain truth represented as composition
availability, or source degradation silently collapsed into `AVAILABLE`.

### 3.8 ReservedContributionSlot

**Purpose.** Declares a future Experience attachment point without implying an
implementation.

**Canonical owner.** Experience Platform.

| Field | Presence | Meaning | Owner |
|---|---|---|---|
| `slot_id` | Required | Stable slot identity | Experience Platform |
| `attachment_class` | Required | M35 attachment class | Experience Platform |
| `accepted_descriptor_contract` | Required | Future descriptor family | Experience Platform |
| `context_requirements` | Required | Required future context | Experience Platform |
| `unfilled_behavior` | Required | `ABSENT` or `UNSUPPORTED` | Experience Platform |
| `compatibility_requirement` | Required | Foundation revision constraint | Experience Platform |
| `slot_state` | Required | `RESERVED` in M38 | Experience Platform |

**Lifecycle.** Declared as `RESERVED` and retained unchanged throughout M38.
A future milestone MAY define binding under a separately approved contract.

**Invariants.** A reserved slot performs no I/O, has no business semantics,
grants no access, and cannot block unrelated content.

**Allowed transitions.** No slot-state transition is allowed in M38.
`RESERVED` is terminal within M38.

**Prohibited M38 states.** Bound, executing, provider-configured, or populated
with placeholder market, Intelligence, Resolver, or action data.

### 3.9 IntentAttachmentSeam

**Purpose.** Reserves the Experience-side route for future proposed human
intent to reach its independently owned gate.

**Canonical owner.** Experience Platform owns the seam contract and its
capture-and-routing mechanics. The seam transfers no ownership: the future
intent owner exclusively owns intent semantics, validation, authority,
decision, and resulting records.

| Field | Presence | Meaning | Owner |
|---|---|---|---|
| `seam_id` | Required | Stable seam identity | Experience Platform |
| `attachment_class` | Required | Governed Product Operations | Experience Platform |
| `required_context_bindings` | Required | Required context references | Experience Platform |
| `owner_binding_requirement` | Required | Exactly one future intent owner | Experience Platform |
| `gate_binding_requirement` | Required | Existing owning gate | Experience Platform |
| `authority_contract_requirement` | Required | Exact M33 contracts where applicable | Experience Platform |
| `unavailable_behavior` | Required | No action affordance when unbound | Experience Platform |
| `seam_state` | Required | `RESERVED` in M38 | Experience Platform |

**Lifecycle.** Declared as `RESERVED` and retained unchanged throughout M38.
A future milestone MAY bind the seam only to an independently owned intent
gate under a separately approved contract.

**Invariants.** The seam owns no intent semantics, authority, decision, or
resulting record; an unbound seam performs no I/O and exposes no action
affordance; navigation and visibility never imply authority.

**Allowed transitions.** No seam-state transition is allowed in M38.
`RESERVED` is terminal within M38.

**Prohibited M38 states.** Captured, submitted, approved, rejected, executed,
permission-bearing, or endpoint-backed intent.

## 4. Ownership matrix

| Boundary | Exclusively owns | May consume | Must not own or infer |
|---|---|---|---|
| Experience Platform | Workspace Identity and Context, Current Selection relationship, Asset Focus relationship, navigation, descriptors, composition availability, transient Discovery Experience, reserved seams | Public Search, exact Registry reads, public projections | Asset identity, candidate standing, provider evidence, Portfolio truth, market facts, Intelligence facts, authority |
| Universal Search | Search request/response, candidate kind, ordering, Search degradation, `claim_id` lifecycle | Registry catalog projections and normalized provider observations | Workspace, Portfolio, Asset Focus, registration, resolution, authority |
| Registry / Asset Foundation | `asset_id`, canonical asset facts, classifications, lifecycle, identity relationships | Governed identity evidence | Workspace, Search ranking, provider observations as truth |
| Resolver | Claim evaluation and identity-resolution verdict | Provider evidence and Registry facts | Workspace navigation, Search presentation, Registry minting |
| Provider adapters | Capability declarations and provider-response normalization | External provider responses | `asset_id`, canonical identity, ranking, workspace, Portfolio, Intelligence |
| Portfolio / Ledger & Accounting | Portfolio Identity, Accounting Scope, ledger truth | Canonical `asset_id` | Current Selection, Search or provider identifiers as identity |
| Market Intelligence | Canonical observations and their provenance/time/quality | Registry-issued identities and provider observations | Asset identity, workspace state, Portfolio truth |
| Intelligence | Its own derived knowledge, judgment, and evidence | Lower-domain canonical facts | Workspace internals, provider dialect, Registry decisions, accounting truth |
| Future Intent owners | Intent semantics, validation, authority, decisions, resulting records | Explicit context and exact authority contracts | Navigation or visibility as authority |

No field or transition has shared ownership. Where a container is Experience-
owned, referenced facts retain their source owner.

## 5. Canonical state machines

The states below describe boundary lifecycles; they do not add fields to or
change the frozen M37 candidate schemas. Each transition has exactly one
canonical owner. A domain that supplies an input or fact causing a transition
does not thereby share ownership of that transition.

### 5.1 Registered Candidate

The Registered Candidate projection remains an immutable M37 Search result.
The states below govern its emission and Experience-side consumption.

| State | Meaning | State owner |
|---|---|---|
| `NOT_EMITTED` | No candidate has been emitted in the Search response | Universal Search |
| `EMITTED` | A structurally valid M37 Registered Candidate is present | Universal Search |
| `SELECTED` | Experience has selected the emitted candidate for an Asset Focus request | Experience Platform |
| `RELEASED` | Experience no longer retains the candidate interaction | Experience Platform |

| Transition | Canonical owner | Preconditions and effect |
|---|---|---|
| `NOT_EMITTED` → `EMITTED` | Universal Search | Search emits the frozen Registered Candidate shape containing a Registry-issued `asset_id` |
| `EMITTED` → `SELECTED` | Experience Platform | User selection initiates a new `REQUESTED` Asset Focus; it does not activate focus |
| `EMITTED` → `RELEASED` | Experience Platform | Search replacement, dismissal, or expiry releases the interaction |
| `SELECTED` → `RELEASED` | Experience Platform | Handoff completion, replacement, dismissal, or expiry releases the interaction |

`RELEASED` is terminal. Forbidden transitions are `NOT_EMITTED` directly to
`SELECTED`, `SELECTED` directly to active Asset Focus, any transition that
changes candidate kind or `asset_id`, and any transition owned by Registry or a
provider adapter. Registry owns the supplied identity facts; it does not own
candidate emission or selection.

### 5.2 Discovery Candidate

The Discovery Candidate projection remains an immutable M37 Search result.
The states below govern its emission and Experience-side consumption.

| State | Meaning | State owner |
|---|---|---|
| `NOT_EMITTED` | No candidate has been emitted in the Search response | Universal Search |
| `EMITTED` | A structurally valid M37 Discovery Candidate is present | Universal Search |
| `OPEN` | Experience has opened a transient Discovery Experience | Experience Platform |
| `CLOSED` | The transient Discovery Experience has ended | Experience Platform |
| `RELEASED` | Experience no longer retains the unopened candidate interaction | Experience Platform |

| Transition | Canonical owner | Preconditions and effect |
|---|---|---|
| `NOT_EMITTED` → `EMITTED` | Universal Search | Search emits the frozen Discovery Candidate shape with structural absence of `asset_id` |
| `EMITTED` → `OPEN` | Experience Platform | Selection creates a transient `DiscoveryExperienceContext` |
| `EMITTED` → `RELEASED` | Experience Platform | Search replacement, dismissal, or expiry releases the interaction |
| `OPEN` → `CLOSED` | Experience Platform | Close, replacement, or expiry ends the transient context |

`CLOSED` and `RELEASED` are terminal. Forbidden transitions are `EMITTED` or
`OPEN` to Asset Focus, route creation, persistence, Registry mutation, Resolver
verdict, or provider access. Provider adapters own witness normalization, not
candidate emission or Experience transitions.

### 5.3 Asset Focus

| State | Meaning | State owner |
|---|---|---|
| `ABSENT` | The Workspace Context has no Asset Focus | Experience Platform |
| `REQUESTED` | Experience holds one `asset_id` pending exact Registry read | Experience Platform |
| `ACTIVE` | The exact Registry read established that the requested canonical asset exists | Experience Platform |
| `REJECTED` | The request failed closed | Experience Platform |

| Transition | Canonical owner | Preconditions and effect |
|---|---|---|
| `ABSENT` → `REQUESTED` | Experience Platform | A registered candidate or explicit canonical deep link supplies one `asset_id` |
| `REQUESTED` → `ACTIVE` | Experience Platform | Successful exact Registry read activates the same `asset_id` |
| `REQUESTED` → `REJECTED` | Experience Platform | Unknown, unavailable, malformed, or mismatched exact read fails closed |
| `ACTIVE` → `ABSENT` | Experience Platform | Focus is cleared |
| `ACTIVE` → `REQUESTED` | Experience Platform | Replacement starts a new request containing the replacement `asset_id` |
| `REJECTED` → `ABSENT` | Experience Platform | Rejected focus is cleared |
| `REJECTED` → `REQUESTED` | Experience Platform | Retry or replacement starts a new request |

`REJECTED` is terminal for the rejected request instance; clearing or retrying
creates a new focus instance. `ABSENT` is terminal for a cleared instance and
the initial state for a new Workspace Context. Forbidden transitions include
`ABSENT` directly to `ACTIVE`, activation without an exact Registry read,
activation from a Discovery Candidate, symbol or provider fallback, and silent
successor substitution. Registry owns the read result and Asset identity;
Experience Platform alone owns every Asset Focus transition.

### 5.4 Workspace Context

| State | Meaning | State owner |
|---|---|---|
| `UNRESOLVED` | Current runtime Workspace identity has not yet been established | Experience Platform |
| `RESOLVED` | Exactly one current runtime Workspace identity has been established | Experience Platform |
| `REJECTED` | Context resolution failed closed | Experience Platform |
| `DISCARDED` | The resolved interaction context has ended | Experience Platform |

| Transition | Canonical owner | Preconditions and effect |
|---|---|---|
| `UNRESOLVED` → `RESOLVED` | Experience Platform | Current-context bootstrap resolves exactly one `WorkspaceDescriptor` |
| `UNRESOLVED` → `REJECTED` | Experience Platform | Bootstrap cannot establish the current runtime Workspace identity |
| `RESOLVED` → `DISCARDED` | Experience Platform | Interaction ends or the context is replaced |

`REJECTED` and `DISCARDED` are terminal for that context instance. Selection,
focus, contribution, and navigation changes are permitted only while
`RESOLVED` and do not change context state. Forbidden transitions include
`REJECTED` to `RESOLVED` on the same instance, multiple current workspaces,
silent switching, inferred workspace identity, and composition before
`RESOLVED`.

### 5.5 Projection Availability

Projection Availability is Experience-owned composition state. Source-domain
availability, quality, and degradation remain source-owned facts carried by
the envelope and are inputs to, not owners of, these transitions.

| State | Meaning | State owner |
|---|---|---|
| `REQUESTED` | Experience is evaluating a declared projection attachment | Experience Platform |
| `AVAILABLE` | Required projection contracts are usable | Experience Platform |
| `DEGRADED` | Projection is usable with visible source qualification | Experience Platform |
| `UNAVAILABLE` | Projection is supported but cannot currently be composed | Experience Platform |
| `UNSUPPORTED` | Required projection capability or implementation does not exist | Experience Platform |
| `DETACHED` | The envelope is no longer attached | Experience Platform |

| Transition | Canonical owner | Preconditions and effect |
|---|---|---|
| `REQUESTED` → `AVAILABLE` | Experience Platform | Required public projection contract is usable without degradation |
| `REQUESTED` → `DEGRADED` | Experience Platform | Projection is usable and source qualification remains visible |
| `REQUESTED` → `UNAVAILABLE` | Experience Platform | Supported projection cannot currently be composed |
| `REQUESTED` → `UNSUPPORTED` | Experience Platform | Required capability or implementation does not exist |
| `AVAILABLE`, `DEGRADED`, or `UNAVAILABLE` → `REQUESTED` | Experience Platform | Refresh starts a new evaluation |
| Any non-`DETACHED` state → `DETACHED` | Experience Platform | Attachment is removed without changing source state |

`UNSUPPORTED` is terminal for that request; `DETACHED` is terminal for that
envelope instance. Forbidden transitions include treating empty payload as
unavailable, treating missing data as zero or current, hiding source
degradation, Experience mutation of source facts, and projection failure
blocking unrelated workspace content.

### 5.6 Transitions reserved outside M38

Claim evaluation and identity-resolution transitions belong exclusively to a
future Resolver. Registry issuance and identity-lifecycle transitions belong
exclusively to Registry. Intent acceptance, rejection, and resulting-record
transitions belong exclusively to the future intent owner and its owning gate.
M38 defines no transition into any of those future state machines.

## 6. Dependency rules

### 6.1 Workspace MAY depend on

- M38 current-workspace bootstrap.
- Exact Registry asset reads.
- Frozen M37 `POST /asset-search`.
- Experience-owned Current Selection state.
- Declared public projection contracts.
- Contribution descriptors and reserved seams.

Every dependency MUST be declared.

### 6.2 Workspace MUST NOT depend on

- Search internals, Resolver internals, provider adapters, provider URLs, or
  provider SDKs.
- Registry persistence or private adjudication.
- Portfolio database state for selection inference.
- Market Intelligence or Intelligence implementation internals.
- Search to reconstruct a direct asset route.
- Undeclared ambient state.

### 6.3 Search, Registry, Resolver, and provider prohibitions

Universal Search MUST NOT accept workspace or portfolio context, mutate domain
state, mint identity, expose `asset_id` on Discovery Candidates, adjudicate,
register, or hide degradation.

The M38 Registry read MUST NOT depend on Workspace, Search, or providers; it MUST
NOT fall back from `asset_id` to symbols or provider identifiers; and it MUST
NOT write or silently substitute successors.

Resolver MUST NOT own navigation, Asset Focus, or presentation and MUST NOT be
exposed by an M38 endpoint.

Provider adapters MUST NOT mint identity, rank candidates, decide standing, or
write Workspace, Registry, or Portfolio state.

### 6.4 Mandatory dependency verification

| Rule family | Objective verification |
|---|---|
| Workspace public-only dependencies | Static dependency test rejects imports from Search internals, Resolver internals, provider adapters, Registry persistence, and private projection implementations |
| Search isolation | Request-schema test rejects Workspace and Portfolio context; call-boundary tests prove Search does not read or mutate Workspace, Portfolio, Resolver, or authority state |
| Exact Registry read isolation | Call-boundary tests prove `GET /assets/{assetId}` does not invoke Search, Resolver, providers, Workspace state, or write paths |
| Provider adapter authority | Static and call-boundary tests prove adapters cannot mint `asset_id`, rank candidates, or write Workspace, Registry, or Portfolio state |
| Direct-route isolation | Integration tests prove canonical deep links perform current-context bootstrap and exact Registry read without invoking Search or providers |
| Reserved seam inertness | Static and runtime tests prove reserved slots and intent seams bind no implementation, perform no I/O, and expose no endpoint or action affordance |
| Declared projection use | Descriptor validation rejects any projection or context dependency absent from `read_dependencies`, `projection_contracts`, or `context_requirements` |

Passing behavior tests without these dependency checks is insufficient. The
implementation MUST supply both structural dependency evidence and runtime
call-boundary evidence where listed.

## 7. Conformance requirements

### 7.1 Identity and routing

- **ID-01:** Every active Asset Focus contains exactly one `asset_id`.
- **ID-02:** Symbols, provider identifiers, `claim_id`, and candidate position
  MUST NOT act as identity.
- **ID-03:** Discovery Candidate structurally excludes `asset_id`.
- **ID-04:** `claim_id` MUST NOT be persisted or routed.
- **RT-01:** Canonical asset navigation contains explicit `workspaceId` and
  `assetId`.
- **RT-02:** Route workspace identity MUST equal the current runtime identity.
- **RT-03:** Mismatch MUST fail closed.
- **RT-04:** Direct asset navigation MUST NOT invoke Search.
- **RT-05:** Discovery Candidate MUST NOT construct an asset route.

### 7.2 Ownership and composition

- **OW-01:** Every contribution has a complete owner map.
- **OW-02:** No concept has multiple owners.
- **OW-03:** Workspace MUST NOT rewrite source facts.
- **CO-01:** Context MUST resolve before composition.
- **CO-02:** Dependencies MUST be public and declared.
- **CO-03:** Optional failure MUST be isolated.
- **CO-04:** Composition MUST NOT create authoritative aggregates.
- **CO-05:** Contribution state MUST be namespaced.
- **CO-06:** Current Selection MUST remain zero-or-one and independent of Asset
  Focus.

### 7.3 Degradation and discovery

- **DG-01:** Available, degraded, unavailable, unsupported, absent, and empty
  MUST remain distinguishable.
- **DG-02:** Degraded and unavailable states MUST be visible and reasoned.
- **DG-03:** Missing data MUST NOT become zero, current, safe, or approved.
- **DG-04:** Search degradation MUST be preserved.
- **DS-01:** Registered and Discovery candidates MUST remain structurally
  distinct.
- **DS-02:** Discovery selection MAY open only a transient Discovery Experience.
- **DS-03:** Discovery Experience MUST NOT persist, route, mutate, or call
  providers.
- **DS-04:** A future resolved `asset_id` MUST enter through a new Asset Focus
  request.

### 7.4 Reserved seams and compatibility

- **AS-01:** All M38 reserved slots and intent seams MUST remain unbound.
- **AS-02:** Unbound seams MUST perform no I/O and expose no action affordance.
- **AS-03:** No concrete market, Intelligence, Resolver, or intent endpoint is
  part of M38.
- **CP-01:** Legacy routes MAY remain.
- **CP-02:** Legacy navigation MAY link canonically only with an existing
  authoritative `asset_id`.
- **CP-03:** Compatibility code MUST NOT resolve symbols merely to redirect.
- **CP-04:** M35, M36, and M37 contracts MUST remain unchanged.

### 7.5 Public read boundaries

- **WB-01:** `GET /workspace-context` MUST return only the minimal descriptor
  for the current runtime workspace.
- **WB-02:** Current-context bootstrap MUST NOT implement a workspace
  directory, workspace switching, membership, RBAC, or default-Portfolio
  behavior.
- **WB-03:** Workspace bootstrap and descriptor presence MUST NOT grant or
  imply authority.
- **RR-01:** `GET /assets/{assetId}` MUST return an exact Registry projection
  whose subject is the requested `asset_id`.
- **RR-02:** Exact Asset reads MUST NOT fall back to symbols, names, provider
  identifiers, Search, or Resolver.
- **RR-03:** Exact Asset reads MUST preserve actual Registry lifecycle and
  identity relationships and MUST NOT silently substitute a successor.
- **RR-04:** Exact Asset reads MUST be read-only and MUST NOT invoke provider
  adapters or Registry mutation paths.

## 8. Public boundary surfaces

### 8.1 Current Workspace bootstrap

| Property | Contract |
|---|---|
| Method and path | `GET /workspace-context` |
| Canonical owner | Experience Platform |
| Request | No Workspace selector, Portfolio selector, Search request, or provider identifier |
| Success result | The minimal current runtime `WorkspaceDescriptor` |
| Failure result | Rejected or unavailable current context; fail closed without substituting another workspace |

The endpoint MUST return only the current runtime workspace descriptor. It MUST
NOT enumerate a workspace directory, select or switch workspaces, expose
membership or RBAC, infer a default Portfolio, or grant authority. Its result
is the only M38 bootstrap input to Workspace Context resolution.

### 8.2 Exact Registry asset read

| Property | Contract |
|---|---|
| Method and path | `GET /assets/{assetId}` |
| Canonical owner | Registry / Asset Foundation |
| Request identity | Exactly one Registry-issued `asset_id` supplied as `assetId` |
| Success result | Exact canonical Asset projection for the same `asset_id`, including its actual Registry lifecycle state and declared identity relationships |
| Failure result | Unknown, malformed, or unavailable exact identity fails closed |

The endpoint MUST perform an exact Registry read. It MUST NOT invoke Search,
Resolver, or provider adapters; fall back to symbols, names, or provider
identifiers; write Registry state; adjudicate a claim; or silently substitute a
successor. A successor relationship MAY be returned as Registry-owned data,
but the requested `asset_id` remains the response subject.

### 8.3 Frozen Universal Search contract

`POST /asset-search` remains owned by Universal Search and frozen under M37.
Workspace MUST consume it only through its public client and MUST NOT extend
its request or response with Workspace, Portfolio, focus, routing, or authority
semantics.

### 8.4 Canonical Experience navigation

`/workspaces/{workspaceId}/assets/{assetId}` is the canonical M38 Asset
Workspace navigation route. It is an Experience navigation contract, not an
Asset Foundation data endpoint. The route MUST reconstruct explicit Workspace
Context, require `workspaceId` to equal the current runtime `workspace_id`, and
create a `REQUESTED` Asset Focus for the same `assetId`. A mismatch or failed
exact Registry read MUST fail closed. The route MUST NOT grant authority,
invoke Search, resolve symbols, or call providers.

### 8.5 Surfaces reserved for future milestones

| Surface | Future canonical owner | M38 status |
|---|---|---|
| Discovery handoff | Resolver | No endpoint; reserved seam only |
| Market projection | Market Intelligence | No endpoint; reserved slot only |
| Intelligence projection | Owning Intelligence domain | No endpoint; reserved slot only |
| Intent or action submission | Future intent owner | No endpoint; reserved seam only |

## 9. Mandatory implementation gates

### 9.1 Contract gates

- All nine contracts and their field owners are present.
- Every transition has one owner.
- No unresolved design decision affects WP2–WP9.
- Reserved slots and intent seams are explicitly unbound.

### 9.2 Routing and identity gates

- Correct workspace plus valid `asset_id` activates focus.
- Workspace mismatch and unknown asset fail closed.
- Deep links do not invoke Search or providers.
- Registered candidates construct canonical navigation.
- Discovery candidates cannot construct canonical navigation.
- Registry successors are displayed as relationships, never silently substituted.

### 9.3 Dependency gates

- Workspace has no imports or calls to Search internals, Resolver internals, or
  providers.
- Exact Registry read has no Search, provider, workspace, or mutation dependency.
- Frontend Search access uses only the shared public Search client.
- Future-domain seams perform no M38 I/O.

### 9.4 State and degradation gates

- Current Selection supports `NONE` and has no default.
- Current Selection and Asset Focus remain independent.
- Discovery Experience leaves no durable state.
- Projection and contribution failures degrade independently and visibly.
- Available, degraded, unavailable, unsupported, absent, and empty states are
  distinguishable.

### 9.5 Compatibility gates

| Test identifier | Mandatory proof |
|---|---|
| `COMP-01` | Existing legacy routes remain operational |
| `COMP-02` | Only an existing authoritative `asset_id` may be used for a canonical link |
| `COMP-03` | No symbol-resolution redirect is introduced |
| `COMP-04` | M35, M36, and M37 artifacts and public contracts remain unchanged |

### 9.6 Mandatory state-machine tests

| Test identifier | Mandatory proof |
|---|---|
| `SM-RC-01` | Every Registered Candidate transition in §5.1 is accepted and every listed forbidden transition is rejected |
| `SM-RC-02` | Selection creates `REQUESTED` Asset Focus and cannot create `ACTIVE` focus directly |
| `SM-DC-01` | Every Discovery Candidate transition in §5.2 is accepted and every listed forbidden transition is rejected |
| `SM-DC-02` | Closing or releasing Discovery state leaves no route, persistence, Asset Focus, Resolver call, or provider call |
| `SM-AF-01` | Every Asset Focus transition in §5.3 is accepted and all other transitions fail closed |
| `SM-AF-02` | Exact Registry success activates the same `asset_id`; unknown identity, mismatch, and unavailable reads reject it |
| `SM-WC-01` | Every Workspace Context transition in §5.4 is accepted and all other transitions fail closed |
| `SM-WC-02` | `REJECTED` and `DISCARDED` context instances cannot compose or return to `RESOLVED` |
| `SM-PA-01` | Every Projection Availability transition in §5.5 is accepted and every listed forbidden transition is rejected |
| `SM-PA-02` | Empty, degraded, unavailable, unsupported, and detached outcomes remain distinguishable |
| `SM-OWN-01` | The transition test map assigns exactly the single owner specified in §5; supplying facts or triggers does not confer transition ownership |

### 9.7 Mandatory public-contract tests

| Test identifier | Mandatory proof |
|---|---|
| `HTTP-WC-01` | `GET /workspace-context` returns only the current minimal `WorkspaceDescriptor` |
| `HTTP-WC-02` | Bootstrap exposes no directory, switching, membership, RBAC, default Portfolio, or authority behavior |
| `HTTP-AR-01` | `GET /assets/{assetId}` returns only the exact same canonical subject and preserves actual lifecycle and successor relationships |
| `HTTP-AR-02` | Unknown, malformed, and unavailable `asset_id` inputs fail closed without fallback, write, adjudication, or substitution |
| `HTTP-AS-01` | `POST /asset-search` matches the frozen M37 public request and response contract without schema or semantic changes |
| `NAV-01` | `/workspaces/{workspaceId}/assets/{assetId}` resolves only when `workspaceId` equals the current runtime identity and the exact Asset read succeeds |
| `NAV-02` | Canonical navigation performs no Search, Resolver, or provider call and grants no authority |
| `SEAM-01` | No public Resolver, market, Intelligence, or intent/action endpoint exists in M38 |

### 9.8 Mandatory contract and ownership tests

| Test identifier | Mandatory proof |
|---|---|
| `CT-01` | All required fields, presence rules, state vocabularies, invariants, allowed transitions, and prohibited states for all nine contracts match §3 |
| `CT-02` | Every instantiated field resolves to exactly one owner under §3 and §4 |
| `CT-03` | Contribution validation rejects an incomplete or multiply assigned `concept_owner_map` |
| `CT-04` | Reserved slots and intent seams remain `RESERVED`, unbound, inert, and non-authoritative |
| `CT-05` | Projection envelopes preserve subject identity, semantic ownership, provenance, temporal context, quality context, and source degradation without reinterpretation |
| `CT-06` | Current Selection supports `NONE`, never defaults, and changes independently of Asset Focus |
| `CT-07` | Dependency checks in §6.4 pass in both structural and runtime forms |

### 9.9 Test-to-conformance traceability

| Mandatory test | Conformance requirements |
|---|---|
| `SM-RC-01`, `SM-RC-02` | `ID-01`, `ID-02`, `DS-01`, `DS-04` |
| `SM-DC-01`, `SM-DC-02` | `ID-03`, `ID-04`, `RT-05`, `DG-04`, `DS-01`, `DS-02`, `DS-03`, `DS-04` |
| `SM-AF-01`, `SM-AF-02` | `ID-01`, `ID-02`, `RT-03`, `RT-04`, `RR-01`, `RR-02`, `RR-03` |
| `SM-WC-01`, `SM-WC-02` | `RT-02`, `RT-03`, `CO-01`, `WB-01`, `WB-02`, `WB-03` |
| `SM-PA-01`, `SM-PA-02` | `CO-03`, `DG-01`, `DG-02`, `DG-03` |
| `SM-OWN-01` | `OW-01`, `OW-02`, `OW-03` |
| `HTTP-WC-01`, `HTTP-WC-02` | `WB-01`, `WB-02`, `WB-03`, `CO-01` |
| `HTTP-AR-01`, `HTTP-AR-02` | `RR-01`, `RR-02`, `RR-03`, `RR-04`, `RT-04` |
| `HTTP-AS-01` | `DS-01`, `DG-04`, `CP-04` |
| `NAV-01`, `NAV-02` | `RT-01`, `RT-02`, `RT-03`, `RT-04`, `ID-01`, `RR-01`, `WB-03` |
| `SEAM-01` | `AS-01`, `AS-02`, `AS-03` |
| `COMP-01`, `COMP-02`, `COMP-03`, `COMP-04` | `CP-01`, `CP-02`, `CP-03`, `CP-04` |
| `CT-01`, `CT-02`, `CT-03` | `OW-01`, `OW-02`, `OW-03`, `CO-02`, `CO-05` |
| `CT-04` | `AS-01`, `AS-02`, `AS-03` |
| `CT-05` | `OW-03`, `CO-03`, `CO-04`, `DG-01`, `DG-02`, `DG-03` |
| `CT-06` | `CO-06` |
| `CT-07` | `CO-02`, `RT-04`, `RR-02`, `RR-04`, `AS-02` |

## 10. Acceptance gate

WP1 is complete only when another engineer can implement WP2–WP9 without
deciding who owns a field, transition, identity decision, degradation state,
or future seam.

Required evidence:

1. This contract specification is reviewed as the canonical boundary document.
2. Every logical field has one owner.
3. Every state transition has one owner.
4. Every dependency rule has an objective verification method.
5. Mandatory tests are mapped to the conformance identifiers above.
6. No M35–M37 amendment is required.
7. No future Resolver, Market Intelligence, Intelligence, or intent behavior is
   implied by an M38 seam.
8. All downstream work packages can reference this document without adding
   architecture-level interpretation.

**WP1 status: SPECIFICATION COMPLETE — READY FOR WP2–WP9 IMPLEMENTATION.**

## 11. Editorial inconsistencies recorded

The following are recorded for traceability and are not silently changed:

1. “Intelligence consumes workspace” is retained only as a composition
   statement. A direct Experience-to-Intelligence dependency would contradict
   the platform dependency law and is therefore prohibited.
2. “Portfolio” is used as a bounded-context shorthand in ownership tables;
   canonical Portfolio Identity and Accounting Scope remain owned by Ledger &
   Accounting, while Current Selection remains Experience-owned.
3. Projection availability and source degradation are intentionally separate:
   Experience owns attachment availability; the source domain owns the factual
   degradation explanation carried inside the envelope.
