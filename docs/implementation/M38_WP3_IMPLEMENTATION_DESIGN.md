M38-WP3 — Asset Focus Runtime Implementation Design
1. Executive summary
WP3 implements the Experience-owned Asset Focus runtime defined by frozen WP1 and integrates it with frozen WP2.
The canonical flow is:
Resolved Workspace Context
        ↓
WP2 Workspace prerequisite validation
        ↓
ABSENT → REQUESTED Asset Focus
        ↓
GET /assets/{assetId}
        ↓
same exact subject: ACTIVE
failure or mismatch: REJECTED
REQUESTED → ACTIVE → REJECTED is not a sequential lifecycle. ACTIVE and REJECTED are mutually exclusive outcomes from REQUESTED. There is no ACTIVE → REJECTED transition.
WP3 neither owns Workspace Context nor canonical Asset identity:
WP2 owns Workspace Context and its lifecycle.
WP3 owns the Asset Focus relationship and its transitions.
Registry owns asset_id, canonical Asset facts, lifecycle facts, and exact-read results.
2. Runtime architecture
Navigation or Registered Candidate
               │
               ▼
Frozen WP2 Workspace prerequisite
               │
               ▼
      Asset Focus Coordinator
        ├── Asset Focus State Machine
        ├── Request-generation control
        ├── Stale-result suppression
        └── Public Exact Asset Read Client
                         │
                         ▼
               GET /assets/{assetId}
WP3 attaches the resulting AssetFocusReference through the frozen WP2 attachment interface. It does not mutate the Workspace Context directly.
3. Runtime components
3.1 Asset Focus state machine
A pure Experience-owned component that:
validates allowed transitions;
constructs immutable AssetFocusReference instances;
rejects every transition not listed by WP1;
performs no HTTP, persistence, Search, provider, or Registry operation.
ABSENT is represented by the structural absence of asset_focus from ProductWorkspaceContext. It is not an AssetFocusReference.focus_state.
3.2 Asset Focus coordinator
The coordinator exclusively owns orchestration of the focus lifecycle. It:
verifies that the frozen WP2 context is still RESOLVED;
consumes WP2’s Workspace-segment validation result for canonical routes;
creates REQUESTED focus;
attaches focus through the WP2 public attachment boundary;
invokes the exact public Asset Read client;
validates that a successful response has the requested asset_id as its subject;
transitions the current request to ACTIVE or REJECTED;
suppresses stale asynchronous completions;
implements clear, retry, replacement, and retirement behavior.
It must not:
change Workspace Context state;
select or switch a workspace;
read or modify Current Selection;
infer authority from context or Asset existence;
interpret Registry facts;
persist Asset Focus;
call Search, Resolver, or providers.
3.3 Exact Asset Read client
The client consumes only:
GET /assets/{assetId}
It must preserve the frozen public contract and expose these outcomes to the coordinator:
exact success for the requested subject;
unknown identity;
malformed request or response;
unavailable identity;
mismatched response subject;
transport or boundary failure.
The client must not:
import Registry persistence, services, models, or adjudication;
fall back to a symbol, name, provider identifier, Search, or Resolver;
follow or substitute successor identity;
mutate Registry state;
call provider adapters;
reinterpret lifecycle or identity relationships.
A response may contain a successor relationship while still identifying the requested asset as its subject. That is a valid exact response; focus remains on the requested asset_id.
3.4 Frozen WP2 integration adapter
This adapter consumes the WP2 public interfaces for:
reading the current resolved context;
validating the Workspace route segment;
attaching, replacing, or clearing asset_focus;
detecting context replacement or discard.
Every attachment is conditional on the same WP2 context instance remaining current and RESOLVED.
The adapter cannot modify:
workspace;
context_state;
current_selection;
active_contribution_id;
navigation_position.
3.5 Asset Focus read interface
Consumers may read or observe:
ABSENT, represented by no reference; or
the current immutable AssetFocusReference.
The interface exposes no Registry payload, provider evidence, authority, Portfolio state, or internal concurrency generation.
4. Runtime contract realization
An instantiated AssetFocusReference contains exactly:
Field	Runtime rule
focus_kind	Required Experience-owned Asset discriminator
asset_id	Required opaque identity value used unchanged for the exact read
focus_state	Exactly REQUESTED, ACTIVE, or REJECTED

Additional identity-bearing fields are prohibited. In particular, the reference cannot contain symbols, provider identifiers, claim_id, candidate position, successor substitution, or Portfolio identity.
Registry projections are not copied into the reference.
5. State-machine realization
Current state	Operation	Result
ABSENT	Valid registered-candidate or canonical-route request	New REQUESTED instance
REQUESTED	Exact success for the same asset_id	Same request becomes ACTIVE
REQUESTED	Unknown, unavailable, malformed, mismatched, or failed exact read	Same request becomes REJECTED
ACTIVE	Clear	Current instance retires; focus becomes ABSENT
ACTIVE	Replace	Active instance retires; new instance begins REQUESTED
REJECTED	Clear	Rejected instance retires; focus becomes ABSENT
REJECTED	Retry or replace	Rejected instance remains terminal; new instance begins REQUESTED

All other transitions fail closed.
In particular:
ABSENT → ACTIVE is forbidden.
ACTIVE → REJECTED is forbidden.
REJECTED → ACTIVE on the same instance is forbidden.
Activation without an exact read is forbidden.
REQUESTED → REQUESTED on the same context instance is not introduced.
6. Request sources
WP3 accepts focus initiation from only:
A Registered Candidate carrying an existing authoritative asset_id.
An explicit canonical route after WP2 validates its workspaceId.
A Discovery Candidate cannot initiate Asset Focus because its frozen M37 shape structurally excludes asset_id.
WP3 does not consume Search responses generally and does not call Search. The caller extracts the Registered Candidate’s existing asset_id before invoking the Asset Focus interface.
7. Canonical navigation integration
For /workspaces/{workspaceId}/assets/{assetId}:
Obtain the current frozen WP2 context.
Require it to be RESOLVED.
Ask WP2 to validate that route workspaceId exactly equals the current runtime workspace_id.
On mismatch, fail closed without creating focus or calling Registry.
On success, create a REQUESTED focus containing the route assetId.
Call the exact public Asset Read endpoint with that same value.
Activate only if the response subject is exactly the requested asset_id.
Otherwise transition the request to REJECTED.
Do not grant or infer authority at any stage.
WP3 completes canonical navigation integration but does not take ownership of the route’s Workspace prerequisite.
8. Replacement, clearing, and discard
Replacement
Replacement is atomic from the observer’s perspective:
the old ACTIVE or REJECTED instance is retired;
a new immutable REQUESTED instance is attached;
the old Asset is not retained as a fallback;
failure of the replacement produces REJECTED, not restoration of the previous active focus.
Clearing
Clearing is permitted only from ACTIVE or REJECTED. It removes asset_focus, producing ABSENT.
Pending requests
WP1 defines no REQUESTED → ABSENT or REQUESTED → REQUESTED transition.
Therefore, while a request is pending:
an identical request may share the existing in-flight result without creating a transition;
a different request in the same context fails closed without changing current focus;
replacement may proceed through a new Workspace Context interaction if WP2 replaces the context.
Discard
WP3 introduces no DISCARDED focus state.
When WP2 discards or replaces its context, WP3:
retires its coordinator instance;
invalidates pending asynchronous work;
detaches observers;
ignores later completions;
performs no Asset Focus transition on the discarded Workspace Context.
The new Workspace Context begins with structurally absent focus.
9. Concurrency and stale-result suppression
Each coordinator instance maintains a private monotonically changing request generation or equivalent opaque correlation mechanism. It is operational metadata, not a public contract or identity.
A read result may change focus only when all conditions still hold:
the coordinator instance is current;
the WP2 context instance is unchanged and RESOLVED;
the request generation remains current;
the attached focus is the same REQUESTED instance;
the response subject equals the requested asset_id.
Otherwise the completion is stale and ignored.
Required race behavior includes:
an old request cannot activate after its context is discarded;
a late failure cannot reject a newer focus;
duplicate completion cannot cause a second transition;
response order cannot override request order;
cancellation is an optimization only—correctness must rely on generation validation.
10. Fail-closed rules
Condition	Required behavior
Workspace Context is not RESOLVED	No focus request and no Registry call
Route workspace mismatch	No focus request and no Registry call
Missing or structurally unusable assetId	No active focus; fail closed
Unknown or unavailable exact identity	REQUESTED → REJECTED
Exact response subject mismatch	REQUESTED → REJECTED
Registry transport or contract failure	REQUESTED → REJECTED
Successor returned instead of requested subject	REQUESTED → REJECTED
Requested subject returned with successor relationship	Activate requested subject; preserve relationship without substitution
Stale completion	Ignore; do not mutate current state
Discovery Candidate input	Reject before focus creation
Search, Resolver, or provider fallback requested	Reject; perform no fallback

11. Public interfaces
WP3 exposes Experience runtime interfaces, not a new HTTP endpoint.
Asset Focus command interface
Supports:
request focus for one asset_id;
replace an ACTIVE or REJECTED focus;
retry a rejected request using a new focus instance;
clear ACTIVE or REJECTED focus.
Every command requires a current resolved WP2 context.
Asset Focus observation interface
Supports:
obtaining the current AssetFocusReference, if present;
observing reference replacement or removal.
It is read-only and exposes no mutation authority.
Exact Asset Read dependency
The only Registry dependency is the frozen public exact-read client contract.
WP3 must not expose:
Asset registration;
claim resolution;
symbol resolution;
provider validation;
successor selection;
Registry mutation;
authority or action submission.
12. Validation rules
WP3 must validate:
exactly one identity input is present;
no symbol, provider identifier, or claim_id substitutes for asset_id;
the Workspace Context is current and RESOLVED;
canonical-route workspace validation succeeded;
the outgoing exact-read identity equals the requested focus identity;
a success response has the same subject identity;
state transitions are valid for the current focus instance;
the asynchronous completion belongs to the current request;
attachment does not modify Current Selection or other context fields.
Validation failure must not invoke fallback behavior.
13. Dependency boundaries
WP3 may depend on:
frozen WP2 public Workspace Context interfaces;
the frozen public exact Asset Read contract;
Experience-owned Asset Focus contracts and transition rules.
WP3 must never depend on:
Registry persistence, private services, adjudication, or implementation models;
Universal Search internals or Search route reconstruction;
Resolver;
provider adapters, URLs, or SDKs;
Portfolio persistence or Current Selection mutation;
Workspace identity creation or lifecycle mutation;
projection, contribution, Intelligence, Intent, action, RBAC, or membership implementations;
undeclared ambient workspace or asset state.
14. Implementation sequence
Implement the immutable AssetFocusReference representation and structural validation.
Implement the pure Asset Focus transition validator.
Implement the public exact Asset Read client boundary.
Implement the coordinator’s request and exact-read orchestration.
Add response-subject validation and fail-closed result mapping.
Add generation-based stale-result suppression.
Implement replacement, retry, clear, and coordinator retirement.
Integrate through frozen WP2 public attachment and Workspace-validation interfaces.
Integrate Registered Candidate and canonical-route entry points.
Add structural dependency, state-machine, concurrency, and end-to-end conformance gates.
15. Conformance mapping
WP1 requirement	WP3 realization
ID-01, ID-02	Exactly one asset_id; no alternate identity
RT-01–RT-04	Explicit canonical route, WP2 equality prerequisite, mismatch closure, no Search
RT-05, DS-02–DS-04	Discovery cannot create focus or route
OW-02, OW-03	Experience owns focus transitions; Registry facts remain unchanged
CO-01	Focus creation requires resolved Workspace Context
CO-02	Only frozen public WP2 and Registry contracts are consumed
CO-06	Focus operations do not read or modify Current Selection
RR-01–RR-04	Exact same-subject, read-only Registry consumption with no fallback or substitution
CP-02, CP-03	Canonical links require existing asset_id; no symbol redirect
SM-AF-01, SM-AF-02	Complete transition and exact-read outcome coverage
NAV-01, NAV-02	Complete canonical navigation integration
CT-01, CT-02, CT-06, CT-07	Contract, ownership, selection independence, and dependency evidence

16. Mandatory acceptance tests
Contract and ownership
Reference contains exactly the three WP1 fields.
Field presence and state vocabulary match WP1.
Experience owns every focus transition.
Registry exclusively owns asset_id and returned Asset facts.
No transition or fact has shared ownership.
State machine
Every transition in WP1 §5.3 succeeds.
Every unlisted transition fails closed.
ABSENT is structural absence, not a reference state.
Rejected requests cannot become active on the same instance.
Clear, retry, and replacement create the required new or absent instance.
Exact reads
Same-subject success activates the requested identity.
Unknown, unavailable, malformed, failed, and mismatched reads reject.
Symbol, name, provider, Search, and Resolver fallback never occurs.
Successor relationships never substitute the requested subject.
Registry projections are not rewritten or copied into Asset Focus.
Workspace integration
Non-resolved WP2 contexts cannot create focus.
Workspace mismatch causes no focus and no Registry call.
Focus attachment does not change Workspace Context state.
Context discard prevents late focus activation.
A new context begins with absent focus.
Current Selection isolation
Focus request, activation, rejection, replacement, retry, clear, and discard leave Current Selection unchanged.
Selection changes do not change Asset Focus.
NONE remains valid throughout every focus state.
Concurrency
Late success from a retired context is ignored.
Late failure cannot reject a newer request.
Duplicate completion produces one transition.
Out-of-order completion cannot overwrite current state.
Correctness remains intact when transport cancellation fails.
Routing and discovery
Correct workspace plus exact same-subject success activates focus.
Workspace mismatch and exact-read failure fail closed.
Canonical navigation invokes neither Search, Resolver, nor providers.
Registered Candidate selection begins at REQUESTED.
Discovery Candidate cannot construct a route or initiate focus.
Dependency enforcement
Static checks reject Registry internal imports.
Static checks reject Search, Resolver, provider, Portfolio persistence, Intelligence, and Intent dependencies.
Runtime spies prove only the exact public Asset Read boundary is called.
No new public Asset Focus HTTP endpoint exists.
M35–M37 and frozen WP2 contracts remain unchanged.
17. Completion criteria
WP3 is complete only when:
AssetFocusReference exactly matches WP1.
All WP1 §5.3 transitions and prohibitions are enforced.
Activation is possible only after an exact same-subject Registry read.
Every failure path closes without fallback or identity substitution.
Replacement, retry, clear, discard, and stale completions preserve instance semantics.
Canonical navigation composes with WP2 without acquiring Workspace ownership.
Current Selection remains unchanged and independent.
Structural and runtime evidence proves public-contract-only dependencies.
SM-AF-01, SM-AF-02, NAV-01, NAV-02, and applicable contract gates pass.
No frozen WP1, WP2, or M35–M37 artifact requires modification.