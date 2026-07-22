M38-WP2 — Workspace Context Runtime Implementation Design
WP2 is implementable without changing WP1 or any M35–M37 contract. No constitutional contradiction was found.
The central implementation decision is to separate:
the server-owned current Workspace bootstrap;
the client-side ProductWorkspaceContext lifecycle;
the existing M36 Current Selection state;
later M38 producers for Asset Focus, contributions, and navigation.
WP2 provides the runtime composition frame. It does not implement those later capabilities.
Canonical authority: [M38 WP1 specification (line 1)](/G:/work/ta/stock-analysis/docs/implementation/M38_WP1_BOUNDARY_CONTRACT_SPECIFICATION.md:1).
1. WP2 scope boundary
WP2 implements:
WorkspaceDescriptor validation and serialization;
GET /workspace-context;
a read-only current Workspace source;
ProductWorkspaceContext state management;
the complete Workspace Context state machine;
composition gating;
the relationship to the existing M36 Current Selection coordinator;
exact current-workspace route comparison;
fail-closed bootstrap, replacement, discard, and concurrency behavior;
public read interfaces for Workspace Context consumers.
WP2 does not implement:
Asset Focus resolution or Registry asset reads;
Universal Search consumption;
Discovery Experience;
Resolver behavior;
provider access;
projections;
contribution activation;
Intelligence;
intent or action submission;
workspace directory, switching, membership, tenancy, or RBAC;
Portfolio persistence or Portfolio selection semantics;
new persistence schemas.
The optional asset_focus, active_contribution_id, and navigation_position fields remain representable in the context contract, but WP2 supplies no capability that creates them. Their future producers must enter through guarded Experience-owned transition interfaces.
2. Runtime architecture
Operational shell
    │
    │ immutable current-workspace binding
    ▼
Current Workspace Reader ── exact operational read
    │
    ▼
GET /workspace-context
    │
    ▼
Public Workspace Client
    │
    ▼
Workspace Context Coordinator
    ├── Workspace Context state machine
    ├── Current Selection adapter ── existing M36 coordinator
    ├── composition gate
    └── exact route-workspace guard
2.1 Server runtime
Component	Responsibility	Explicit prohibition
Current Workspace Binding	Holds exactly one process/runtime Workspace Identity established by the operational shell	No directory, switching, membership, RBAC, Portfolio default, or authority
Current Workspace Reader	Reads the bound identity exactly and creates a minimal descriptor	No create-on-read, first-row selection, fallback, or Portfolio access
Workspace Bootstrap Service	Converts the reader outcome into the public endpoint result	No inferred identity or alternative workspace
Workspace Context Router	Exposes GET /workspace-context	No request selectors or business behavior

The existing get_default_workspace() behavior in [database.py (line 647)](/G:/work/ta/stock-analysis/backend/models/database.py:647) must not be invoked from the HTTP bootstrap path. It creates state when none exists and chooses the first row, neither of which is valid fail-closed runtime bootstrap behavior.
Existing application initialization may continue to establish the single-user workspace before serving requests. WP2 consumes the resulting exact identity through an immutable runtime binding.
2.2 Client runtime
Component	Responsibility
Workspace Public Client	Calls only GET /workspace-context and validates its exact response
Context Transition Engine	Pure implementation of the WP1 Workspace Context state machine
Workspace Context Coordinator	Owns bootstrap sequencing, instance replacement, discard, and stale-result rejection
Current Selection Adapter	Reads the existing M36 Current Selection and attaches its zero-or-one relationship
Composition Gate	Makes product composition available only while context is RESOLVED
Route Workspace Guard	Compares a route workspaceId against the resolved current identity
Read-only Context Interface	Publishes the canonical context snapshot to Experience consumers

The Current Selection implementation in [PortfolioContext.tsx (line 1)](/G:/work/ta/stock-analysis/frontend/lib/PortfolioContext.tsx:1) remains canonical. WP2 must subscribe to it; it must not duplicate its storage, validation, persistence key, portfolio list, or transition logic.
3. Runtime contract realizations
3.1 WorkspaceDescriptor
The public representation contains only:
Field	Runtime validation
workspace_id	Required stable Workspace Identity; serialized losslessly and treated opaquely
display_label	Optional presentation string; never used for identity, routing, or equality
descriptor_state	Exactly RESOLVED, UNAVAILABLE, or REJECTED

The current repository uses an integer Workspace primary key. WP2 may preserve that wire representation, but all Workspace runtime code must treat it as an opaque identity—no arithmetic, ordering, list-position, or label-based semantics.
Unknown fields in a successful bootstrap response must be rejected by strict contract validation. This prevents directory, authority, membership, Portfolio, or other fields from entering the public contract accidentally.
3.2 ProductWorkspaceContext
Canonical published states are:
Context state	Required shape	Composition
UNRESOLVED	workspace absent; all compositional fields absent	Forbidden
RESOLVED	Exactly one RESOLVED descriptor; optional Current Selection and later attachments	Allowed
REJECTED	No compositional fields; a REJECTED descriptor may be retained	Forbidden
DISCARDED	Prior descriptor retained; compositional fields detached	Forbidden

On discard, WP2 removes the context’s selection attachment, focus, active contribution, and navigation position. This does not clear or mutate the independently maintained M36 Current Selection.
Async diagnostics, retry counters, request identifiers, and error text are runtime-operation metadata. They must not be added to ProductWorkspaceContext.
4. Runtime services and interfaces
4.1 Current Workspace Reader
Input:
the operational shell’s exact current Workspace Identity binding.
Output is exactly one of:
resolved descriptor;
unavailable descriptor for the same known identity;
rejected descriptor for the same known identity;
source failure without a valid descriptor.
Rules:
The reader performs an exact identity lookup.
It performs no insert, update, delete, commit, fallback, directory query, or first-row selection.
A returned record whose identity differs from the binding is rejected.
Multiple records are rejected.
A missing bound record is unavailable; another workspace is never substituted.
4.2 Workspace Context Coordinator
The coordinator owns:
creation of a new UNRESOLVED context instance;
one bootstrap operation per attempt;
transition to RESOLVED or REJECTED;
synchronization of Current Selection while resolved;
transition from RESOLVED to DISCARDED;
creation of a new instance for retry or replacement;
suppression of stale asynchronous results.
Consumers receive a read-only context. They must not receive a general-purpose setter.
4.3 Current Selection Adapter
The adapter:
maps M36 NONE to absent current_selection;
maps a valid current Portfolio Identity to current_selection.portfolio_id;
updates the relationship only while the Workspace Context is RESOLVED;
never selects a Portfolio;
never loads or owns Portfolio data;
never infers a default;
never changes Asset Focus;
never treats selection as authority.
4.4 Future field attachment boundary
WP2’s internal transition engine must reserve guarded operations for replacing or clearing:
asset_focus;
active_contribution_id;
navigation_position.
WP2 exposes no public producer for these operations. Later M38 work packages must supply their validated Experience-owned coordinators. Arbitrary consumers must not be able to write these fields directly.
5. Lifecycle implementation
5.1 Initial bootstrap
Create a new context instance in UNRESOLVED.
Do not compose product contributions.
Request GET /workspace-context.
Strictly validate the response.
On one valid RESOLVED descriptor, transition to RESOLVED.
Attach the current M36 selection, if one exists.
Open the composition gate.
Any malformed, missing, rejected, unavailable, ambiguous, or transport-failed result transitions that attempt to REJECTED.
5.2 Retry
REJECTED is terminal for the failed context instance.
Retry must:
retain the failed instance only as historical runtime state if diagnostics require it;
create a new UNRESOLVED instance;
start a new bootstrap operation.
The rejected instance must never transition back to RESOLVED.
5.3 Discard and replacement
When the interaction ends or the context is replaced:
transition the resolved instance to DISCARDED;
close its composition gate;
detach its compositional fields;
cancel or invalidate its outstanding work;
create a new UNRESOLVED instance if replacement is required.
5.4 Loss of availability
If a previously resolved workspace becomes unavailable:
discard the resolved context;
do not substitute another workspace;
begin a new context instance only if revalidation or retry is required;
reject that new attempt if bootstrap cannot establish the current workspace.
This preserves the frozen transition rule: an existing RESOLVED context does not transition directly to REJECTED.
5.5 Concurrency
Each context instance requires an internal generation identity that is not part of the public contract.
A bootstrap or attachment result may update state only when:
its generation is still current;
the context has not been discarded;
the expected source state still matches.
Late results from discarded, replaced, or rejected instances must be ignored.
6. HTTP behavior
6.1 GET /workspace-context
Request:
no body;
no query parameters;
no Workspace selector;
no Portfolio selector;
no Search or provider identifiers.
Responses:
Outcome	HTTP behavior	Canonical payload
Current workspace resolved	200	Minimal WorkspaceDescriptor with RESOLVED
Known bound workspace unavailable	404	Minimal descriptor for the same identity with UNAVAILABLE
Known identity rejected by validation	409	Minimal descriptor for the same identity with REJECTED
No valid runtime binding or operational source failure	503	Transport error; no fabricated descriptor

Existing transport authentication may remain unchanged. WP2 adds no authorization policy. A 200 response and descriptor presence do not grant or imply authority.
The endpoint must not cache or return a previously resolved descriptor after its source reports failure or unavailability.
7. Route validation
WP2 supplies the current-workspace portion of the Workspace Route-Context Validator for:
/workspaces/{workspaceId}/assets/{assetId}
The guard succeeds only when:
the context is RESOLVED;
the route identity is valid in the canonical Workspace Identity representation;
it exactly equals context.workspace.workspace_id.
Failure closes the route before Asset Focus or any contribution is composed.
The guard must not:
inspect assetId;
invoke Search, Registry, Resolver, providers, or Portfolio;
compare labels;
coerce another identity type into Workspace Identity;
switch the runtime workspace.
Asset validation and focus activation remain outside WP2.
This validator validates only the Workspace segment of canonical Asset Workspace navigation. It does not expose or complete the canonical navigation transaction defined by WP1 §8.4.
8. Validation rules
The implementation must reject:
missing or empty workspace_id;
unknown descriptor states;
non-resolved descriptors used to resolve a context;
additional bootstrap fields outside the minimal descriptor;
multiple current workspace results;
response identity differing from the operational binding;
composition while unresolved, rejected, or discarded;
updates to a terminal context instance;
Current Selection attachment before resolution;
more than one Current Selection;
inferred or first-Portfolio selection;
route/workspace mismatch;
late completion from an obsolete generation;
direct mutation of the public context snapshot.
9. Failure isolation
Failure	Required behavior
Bootstrap transport failure	New context attempt becomes REJECTED
Missing runtime binding	Fail closed; no workspace inferred
Bound workspace missing	Report unavailable; no fallback
Malformed descriptor	Reject the context
Workspace identity mismatch	Reject the context
Current Selection is NONE	Resolve context with no selection
Current Selection becomes stale	Consume M36’s resulting NONE; do not choose another
Route workspace mismatch	Block route composition
Late bootstrap completion	Ignore it
Context discarded during bootstrap	Ignore completion and retain terminal state

No failure may invoke Search, Resolver, providers, Market, Intelligence, Intent, or Portfolio mutation.
10. Implementation sequence
Contract realization
Define exact runtime representations and strict validators for WorkspaceDescriptor and ProductWorkspaceContext.
Define the pure Workspace Context transition engine.

Operational binding
Introduce the immutable current-workspace binding.
Add an exact, read-only Current Workspace Reader.
Keep creation and initialization outside request handling.

HTTP bootstrap
Add the bootstrap application service and GET /workspace-context.
Register the router without changing existing public contracts.

Public client
Add the endpoint client and strict response parser.
Keep it separate from Search and Portfolio API clients.

Context coordinator
Implement bootstrap, generation control, terminal states, retry-as-new-instance, discard, and replacement.

Current Selection integration
Attach the existing M36 Current Selection through a read-only adapter.
Add no new selection persistence.

Composition and route guards
Prevent composition outside RESOLVED.
Add exact current-workspace matching for canonical routes.

Conformance gates
Add state-machine, HTTP, dependency, concurrency, and integration tests.
Verify M35–M37 artifacts remain unchanged.

This order establishes pure invariants before I/O and prevents later Asset Focus or contribution work from bypassing the context boundary.
11. WP1 conformance mapping
WP1 requirement	WP2 implementation evidence
RT-02, RT-03	Exact route/current identity guard and mismatch tests
OW-02	Singular field and transition ownership
CO-01	Composition gate opens only after RESOLVED
CO-02	Static dependency checks and declared bootstrap client
CO-06	M36 selection adapter and independence tests
WB-01	Minimal endpoint response test
WB-02	Schema, dependency, and negative endpoint tests
WB-03	No authority fields or authorization inference
SM-WC-01	Complete valid and forbidden transition suite
SM-WC-02	Terminal-instance and composition prohibition tests
HTTP-WC-01	Exact response contract test
HTTP-WC-02	Directory/switch/RBAC/default negative tests
CT-01	Contract vocabulary and prohibited-state tests
CT-02	Field-owner and transition-owner assertions
CT-06	NONE, no default, and focus-independence tests
CT-07	Structural and runtime dependency checks

Registry reads, Search, Discovery, projection availability, reserved seams, and compatibility gates remain assigned to their corresponding later M38 work packages.
12. WP2 mandatory acceptance tests
Contract and lifecycle
Every permitted Workspace Context transition succeeds.
Every unlisted transition fails closed.
REJECTED and DISCARDED instances cannot return to RESOLVED.
Retry creates a new context instance.
Composition is inaccessible outside RESOLVED.
Discard detaches all compositional state.
Bootstrap
The endpoint returns only the minimal resolved descriptor.
The endpoint accepts no selectors.
Missing, unavailable, malformed, mismatched, and ambiguous sources fail closed.
Request handling performs no workspace creation or mutation.
No fallback workspace is selected.
No Portfolio, Search, Registry, Resolver, provider, authority, or future-domain call occurs.
Current Selection
NONE remains no selection.
No Portfolio is auto-selected.
Set, clear, and replacement changes are reflected only while resolved.
Selection changes do not affect Asset Focus.
Focus changes do not affect selection.
WP2 introduces no second selection persistence mechanism.
Routing and concurrency
Exact workspace identity match passes.
Mismatch and unresolved context fail.
Labels and Portfolio identifiers cannot satisfy the route guard.
Late bootstrap results cannot mutate replaced or discarded contexts.
Concurrent bootstrap calls cannot publish multiple resolved contexts.
Structural evidence
Dependency tests reject imports from Search internals, Resolver, provider adapters, Market, Intelligence, Intent, and Portfolio persistence.
The bootstrap read path contains no insert, update, delete, commit, or create-on-read operation.
No database migration is introduced.
Frozen M35, M36, M37, and WP1 artifacts remain unchanged.
13. Completion criteria
WP2 is complete when:
Exactly one Workspace Context runtime instance is publicly current.
Its lifecycle exactly implements WP1 §5.4.
Bootstrap is current-only, minimal, read-only, and fail-closed.
Composition cannot occur before successful resolution.
Current Selection is consumed from the frozen M36 implementation without duplication.
Route workspace matching is exact and cannot switch context.
Terminal states and stale async results cannot mutate active state.
All mapped conformance tests pass.
Structural dependency evidence proves prohibited domains are absent.
No M35–M37 or WP1 artifact requires modification.
WP2 implementation design status: COMPLETE — READY FOR IMPLEMENTATION.
No repository files were modified.