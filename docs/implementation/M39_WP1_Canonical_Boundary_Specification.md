M39-WP1 — Canonical Boundary Specification
Status: Canonical and frozen
Milestone: M39 — Canonical Asset Market Observation
Document role: Authoritative boundary contract for all subsequent M39 work packages
Normative language: MUST, MUST NOT, SHALL, SHALL NOT, MAY, and SHOULD are normative.
1. Purpose
M39 establishes an authenticated, read-only Market Intelligence boundary through which a registered asset’s current market observation may be requested using its canonical asset_id.
M39 SHALL:
expose one provider-neutral market-observation resource;
preserve Market Intelligence ownership of observation semantics;
use Registry identity only to address the observed asset and derive the exact configured provider request;
reuse existing canonical Market Data normalization;
remain structurally and semantically separate from execution evidence;
preserve all M31–M38 contracts unchanged; and
bind the M39 contribution through the market attachment point reserved by M38 under a separately governed M39 binding contract.
This specification creates no execution authority, transaction authority, identity authority, provider-routing authority, or accounting truth.
2. Scope
M39-WP1 defines:
the public read boundary:
GET /assets/{assetId}/market-observation

the canonical MarketObservation contract;

the specialization of the frozen M38 ProjectionEnvelope used by that resource;

source availability semantics;

exact asset_id-to-provider-request derivation;

ownership and dependency boundaries;

provider-interface compatibility requirements;

execution-evidence separation;

M38 reserved-contribution declaration and binding rules;

feature-boundary expectations;

conformance, acceptance, and rollback criteria.

The endpoint is additive to the existing HTTP surface.
3. Out of Scope
M39 SHALL NOT include:
execution-price selection;
execution eligibility, freshness acceptance, or transaction admission;
order creation, trade intent, quantity, fees, funding, lots, or fractional-share decisions;
canonical execution-plan adoption of M32 evidence;
changes to M31 or M32 execution behavior;
changes to ExecutionQuoteEnvelope;
changes to existing provider methods or their behavior;
changes to existing quote dictionary contracts;
provider ranking, routing, failover, or fallback;
client-selected providers or provider symbols;
symbol discovery, fuzzy matching, or symbol transformation;
Resolver or Search participation;
asset registration, identity adjudication, Registry remediation, or Registry writes;
automatic successor substitution;
historical observations, observation series, streaming, subscriptions, or bulk observation requests;
new cache policy, cache schema, or persistence;
currency inference, currency conversion, FX, or portfolio valuation;
market-data quality scoring redesign;
modification or recreation of the frozen M38 reserved slot;
binding of any Resolver, Intelligence, or intent seam;
redesign of existing HTTP error contracts;
changes to authentication, authorization, workspace, portfolio, ledger, or transaction contracts.
4. Canonical Vocabulary
4.1 Market Observation
A Market Observation is a Market Intelligence-owned, read-only statement about the observed market value of one canonical asset, together with its semantic kind, temporal evidence, provenance, and qualifications.
A Market Observation is evidence. It is not ledger truth, an executable quote, an execution decision, or transaction authority.
4.2 MarketObservation
MarketObservation is the canonical M39 data contract representing one Market Observation.
It SHALL be structurally distinct from every M31 or M32 execution-evidence contract.
4.3 Execution Evidence
Execution Evidence means evidence governed by the frozen M31–M32 execution contracts, including ExecutionQuoteEnvelope and ExecutionPriceObservation.
Execution Evidence MAY be an already-normalized evidence source for an M39 observation. It SHALL NOT become the public M39 contract, and its availability SHALL NOT imply that an asset is executable.
4.4 Addressing Identity
The path parameter assetId is an addressing identity. It identifies the subject being requested.
Its use beneath /assets SHALL NOT transfer ownership of the resulting Market Observation to Registry or Asset Foundation.
4.5 Provider Request Symbol
The Provider Request Symbol is the exact current Registry identifier value selected under §9. It is boundary evidence used solely to address the configured provider.
It is not canonical asset identity and SHALL NOT become the response subject.
4.6 Source Availability
Source Availability describes whether the Market Intelligence resource can provide a usable Market Observation for the request.
It is distinct from M38 ContributionAvailability, which describes whether Experience can compose a contribution.
4.7 No Symbol Fallback
No symbol fallback means that no symbol, name, identifier, relationship, Search result, Resolver result, provider discovery result, or derived spelling other than the single exact mapping selected under §9 may be used for the provider request.
4.8 Reserved Market Contribution
The reserved market contribution is the Market Intelligence projection attachment point already declared by M38.
M39 does not declare that reserved slot again. M39 declares the concrete contribution descriptor and a separate binding contract that references the existing slot.
5. Ownership Model
Concept or boundary	Canonical owner	Ownership rule
asset_id and asset existence	Registry / Asset Foundation	Registry exclusively determines whether the addressed asset exists
Provider-symbol mapping custody	Registry / Asset Foundation	Registry owns the current mapping record and its lifecycle
Provider response claims	Provider source	Provider remains the source of the external evidence
Provider-response normalization	Market Data provider boundary	Existing canonical normalization rules remain authoritative
MarketObservation semantics	Market Intelligence	Market Intelligence exclusively owns the observation contract and its meaning
Market-observation HTTP resource	Market Intelligence	The /assets path prefix conveys addressing, not semantic ownership
Projection envelope grammar	Experience Platform	The frozen M38 envelope grammar remains Experience-owned
Projection payload facts	Market Intelligence	Enclosure by Experience does not transfer ownership
Contribution descriptor and binding	Experience Platform	Experience owns declaration, compatibility, attachment, and composition mechanics
Reserved market slot	Experience Platform	Its frozen M38 declaration and historical state remain unchanged
Execution evidence	Existing M31–M32 owners	M39 gains no execution ownership
Authentication and HTTP transport	Existing platform owners	M39 reuses existing contracts without amendment

Every concept SHALL have exactly one semantic owner. Reference, addressing, transport, or composition SHALL NOT create shared ownership.
Registry SHALL NOT own, interpret, validate, or qualify a Market Observation merely because Registry owns its subject identity or provider-symbol mapping.
6. Public Boundary
6.1 Resource
Property	Normative contract
Method and path	GET /assets/{assetId}/market-observation
Semantic owner	Market Intelligence
Operation class	Authenticated, read-only retrieval
Addressing input	Exactly one canonical asset_id supplied as assetId
Successful representation	M38 ProjectionEnvelope specialized for a Market Intelligence MarketObservation
Mutation	None
Provider selection input	None
Search or Resolver input	None

6.2 Projection specialization
The public representation MUST conform to the frozen M38 ProjectionEnvelope grammar with:
projection_kind identifying the M39 market-observation contract;
subject_reference containing the exact requested asset_id;
semantic_owner identifying Market Intelligence;
payload containing a MarketObservation only when permitted by §8;
provenance, temporal context, quality context, and degradation preserved according to their source meaning; and
one source-availability state.
The envelope SHALL NOT rename, reinterpret, or duplicate observation semantics.
6.3 Boundary isolation
The endpoint:
MUST perform no Registry mutation;
MUST perform no Search or Resolver operation;
MUST NOT establish, replace, or mutate Asset Focus;
MUST NOT require Workspace Context as a Market Intelligence dependency;
MUST NOT accept a workspace, portfolio, provider, symbol, market, or execution selector;
MUST NOT grant transaction or execution authority; and
MUST NOT block unrelated M38 workspace content when its projection is unavailable.
7. Request and Response Semantics
7.1 Request
The request MUST contain exactly one assetId path value.
The request SHALL use existing authentication and HTTP request conventions. M39 SHALL NOT define a new authentication, tenancy, authority, or permission model.
The client MUST NOT supply:
a provider name or identifier;
a provider symbol;
a canonical or display symbol;
an exchange suffix;
an alternate identifier;
an execution side;
a quantity;
a portfolio or workspace selector; or
fallback instructions.
7.2 Subject preservation
For every successfully addressed request:
the response subject MUST equal the requested asset_id;
the provider symbol MUST NOT replace the response subject;
a successor relationship MUST NOT replace the response subject;
provider-returned identity text MUST NOT replace or amend the response subject; and
provider disagreement about the subject MUST fail closed as specified in §8.
7.3 Validation and not-found behavior
A malformed assetId MUST use the existing HTTP request-validation rejection contract. It SHALL NOT be represented as UNSUPPORTED.
A syntactically valid but unknown asset_id MUST use the existing typed not-found contract. It SHALL NOT cause provider access and SHALL NOT be represented as UNSUPPORTED.
Existing authentication and transport failures SHALL retain their existing HTTP semantics.
7.4 Successful resource outcomes
For a syntactically valid, known asset, the resource MUST return exactly one of:
AVAILABLE;
DEGRADED;
UNAVAILABLE; or
UNSUPPORTED.
These states describe the requested Market Intelligence source projection. They SHALL NOT be used to represent authentication failure, malformed input, or unknown identity.
The resource MUST NOT fabricate a successful Market Observation merely to avoid an unavailable or unsupported result.
8. Availability Model
8.1 States
State	Meaning	Payload rule	Retry meaning
AVAILABLE	A usable Market Observation satisfies the complete M39 availability floor defined below	MarketObservation required	Refresh MAY produce newer evidence
DEGRADED	A usable Market Observation exists, but expected evidence is absent, conditionally applicable evidence is missing, or the observation carries an explicit completeness qualification	MarketObservation required	Retry MAY recover the missing or qualified evidence
UNAVAILABLE	The capability is supported, but no usable observation can currently be produced safely	MarketObservation MUST be absent	Retry MAY succeed without a capability change
UNSUPPORTED	The required mapping, capability, or M39 provider support does not exist, or the provider explicitly reports permanent noncoverage	MarketObservation MUST be absent	Retry SHALL NOT be represented as useful until capability, mapping, implementation, or coverage changes

A payload is structurally valid only when all of the following fields are present and valid:
contract_revision;
subject_asset_id;
price;
price_kind; and
provenance.

For M39 v1, AVAILABLE additionally requires expected-present evidence for:
currency;
observed_at;
received_at; and
market_session.

An absent value, or a canonical sentinel whose meaning is that the expected evidence is unknown or unavailable, SHALL NOT satisfy the expected-present requirement.

The following fields are conditionally applicable:
cached_at is applicable when the observation was obtained from cache;
quality_context is applicable when the source supplies a normalized quality or completeness qualification; and
warnings is applicable when normalized evidence qualifications exist.

A conditionally applicable field MAY be absent when its corresponding condition does not exist. Such absence alone SHALL NOT cause DEGRADED.

A usable observation MUST be classified as DEGRADED when:
any expected-present field is absent or semantically unknown;
an applicable conditional field is absent; or
quality_context or warnings explicitly identifies a completeness or evidence limitation.

AVAILABLE therefore requires:
every structurally required field;
every expected-present field;
every field applicable to the actual evidence path; and
no explicit qualification indicating an evidence or completeness gap.

This availability floor does not establish an execution-freshness policy, cache-acceptance policy, market-session eligibility rule, or transaction-admission rule.

8.2 Required classification
Condition	Required outcome
Malformed assetId	Existing HTTP validation rejection
Unknown asset_id	Existing typed not-found result
Registry read unavailable	UNAVAILABLE
No qualifying current provider-symbol mapping	UNSUPPORTED
Multiple or contradictory qualifying mappings	UNAVAILABLE, with integrity qualification
Configured provider lacks the M39 capability	UNSUPPORTED
M39 support is absent for the configured provider	UNSUPPORTED
Provider explicitly reports permanent noncoverage for the exact symbol	UNSUPPORTED
Provider timeout, outage, or rate limitation	UNAVAILABLE
Empty or malformed provider evidence without authoritative permanent noncoverage	UNAVAILABLE
Provider evidence identifies a different subject	UNAVAILABLE
Usable observation that does not satisfy the complete AVAILABLE floor in §8.1	DEGRADED
Usable observation satisfying the complete AVAILABLE floor in §8.1	AVAILABLE

8.3 UNSUPPORTED boundary
UNSUPPORTED MUST be returned only when at least one of the following is established:
the exact Registry mapping required by §9 does not exist;
the configured provider does not declare or expose the M39 observation capability;
no additive M39 provider support exists;
the provider explicitly and authoritatively reports permanent noncoverage for the exact request.
Transient incidents, malformed provider payloads, ambiguous evidence, mapping contradictions, and subject mismatches MUST NOT be classified as UNSUPPORTED.
A disabled feature boundary MUST NOT be misrepresented as source UNSUPPORTED.
8.4 Availability separation
Source availability and M38 ContributionAvailability MUST remain distinct.
A source AVAILABLE result does not prove that the Experience contribution is enabled or composable. An Experience contribution being ABSENT or UNAVAILABLE does not change the Market Intelligence source’s truth.
9. Provider Derivation Rules
9.1 Frozen M39 v1 provider tuple
M39 v1 SHALL use exactly this provider derivation:
Derivation component	Exact value
Normalized provider path	yahoo_chart
Registry identifier type	PROVIDER_SYMBOL
Registry source namespace	yfinance
Provider request value	Exact value of the unique qualifying current Registry identifier
Provider selection authority	Server-owned; not client-selectable

The normalized provider path yahoo_chart identifies the existing YahooChartProvider path. It is not a new literal PRICE_PROVIDER selector value.

PRICE_PROVIDER remains the existing server-owned provider-selection mechanism. Under its frozen existing contract, the default or yahoo selection resolves to YahooChartProvider, while yfinance resolves to the legacy yfinance-backed provider. M39 SHALL NOT rename, reinterpret, or change those selection semantics.

The M39 v1 tuple is satisfied only when the effective provider selected by the existing mechanism is the normalized yahoo_chart path. If the effective configured provider is another path and no additive M39 support exists for it, the M39 source MUST be classified as UNSUPPORTED under §8.2 and §8.3.

The Registry source namespace yfinance identifies the custody namespace of the required PROVIDER_SYMBOL record. It does not select a runtime provider and MUST NOT be interpreted as equivalent to PRICE_PROVIDER=yfinance.

The normalized provider path, PRICE_PROVIDER selection, and Registry source namespace are distinct concepts. None SHALL be treated as an alias for another.
9.2 Derivation procedure
For each request, the derivation MUST:
validate assetId under the existing canonical asset_id syntax;

perform an exact Registry read for that same asset_id;

retain that asset_id as the sole response subject;

inspect current Registry identifier evidence for that asset;

identify records satisfying all of:
identifier type is exactly PROVIDER_SYMBOL;
current status is true;
source is exactly yfinance;
value is present and non-empty;

require exactly one such qualifying record; and

pass that record’s stored identifier value unchanged as the provider request symbol.

The cardinality outcomes are frozen:
zero qualifying records MUST produce UNSUPPORTED under §8.2 and §8.3;
exactly one qualifying record permits provider request derivation; and
multiple or contradictory qualifying records MUST produce UNAVAILABLE with an integrity qualification under §8.2.

No provider request SHALL occur for the zero, multiple, or contradictory mapping outcomes.

The derivation MUST NOT write, repair, supersede, infer, normalize, or otherwise mutate Registry data.
9.3 Meaning of unchanged
“Unchanged” means byte-for-byte semantic pass-through of the Registry identifier value to the provider request boundary.
M39 MUST NOT:
change case;
add or remove an exchange suffix;
strip punctuation;
rewrite a depositary-receipt spelling;
translate between vendor symbol conventions;
use an exchange or market field to construct a symbol;
use a provider-returned suggested symbol;
try an alternate spelling after failure.
9.4 No fallback sources
When no qualifying mapping exists, M39 MUST NOT substitute:
canonical_symbol;
display_symbol;
any name or display label;
any other identifier type;
a historical or non-current mapping;
a mapping for another provider namespace;
Search output;
Resolver output;
provider discovery or fuzzy matching;
another provider;
a related asset;
a successor asset;
a predecessor asset;
a derived market suffix.

Zero qualifying mappings MUST produce UNSUPPORTED as specified in §8.2, §8.3, and §9.2.

Multiple or contradictory qualifying mappings MUST produce UNAVAILABLE with an integrity qualification as specified in §8.2 and §9.2.

Neither outcome permits fallback, guessing, transformation, or provider access.
10. MarketObservation Contract
10.1 Contract fields
Field	Presence	Meaning	Semantic owner
contract_revision	Required	Exact string "1" for the initial M39 MarketObservation contract	Market Intelligence
subject_asset_id	Required	Exact canonical asset identity addressed by the request and referenced as the observation subject	Market Intelligence owns this field and its observation semantics; Registry owns the referenced asset identity and existence
price	Required	Provider-observed numeric market value	Market Intelligence
price_kind	Required	Canonical normalized meaning of the price	Market Intelligence
currency	Optional in contract; expected-present for AVAILABLE	Provider-supplied normalized currency evidence	Market Intelligence
observed_at	Optional in contract; expected-present for AVAILABLE	Time the provider states the market observation occurred	Market Intelligence
received_at	Optional in contract; expected-present for AVAILABLE	Time the provider response was received at the provider boundary	Market Intelligence
cached_at	Conditionally applicable	Cache provenance time when the observation was obtained from cache	Market Intelligence
market_session	Optional in contract; expected-present for AVAILABLE	Canonical normalized session evidence	Market Intelligence
provenance	Required	Source and evidence lineage	Market Intelligence
quality_context	Conditionally applicable	Source-defined completeness or quality qualification, when one exists	Market Intelligence
warnings	Conditionally applicable	Explicit normalized evidence qualifications, when any exist	Market Intelligence

The exact initial contract_revision value is "1". Later revision values are outside M39-WP1 and require separately approved authority.

Ownership of subject_asset_id does not transfer asset identity authority to Market Intelligence. Market Intelligence owns the field’s inclusion and meaning within MarketObservation; Registry remains the sole owner of the identity to which that field refers.

Field presence and availability classification MUST conform to §8.1.

10.2 Required semantics
The contract MUST preserve the distinction among:
observation time;
provider receipt time; and
cache time.
received_at and cached_at MUST NOT be substituted for observed_at.
A missing currency, time, session, quality field, or warning MUST remain explicitly absent. It MUST NOT be populated from Registry, workspace, portfolio, local clock inference, market convention, or another provider response.
price_kind, market_session, provenance, and warning meanings MUST reuse the existing canonical normalization vocabulary. M39 SHALL NOT create a duplicate normalization vocabulary.
10.3 Structural distinction from execution evidence
MarketObservation:
MUST NOT be assignment-compatible or interchangeable with ExecutionQuoteEnvelope, ExecutionPriceObservation, or any execution input;
MUST NOT contain execution side;
MUST NOT contain executable or accepted price;
MUST NOT contain execution eligibility;
MUST NOT contain execution freshness acceptance;
MUST NOT contain fees, quantity, lots, fractional support, funding, cash-floor, transaction-admission, intent, or authority fields;
MUST NOT expose an execution evidence reference as though it were an M39 observation identity; and
MUST NOT satisfy any execution contract merely because its fields originated from normalized execution evidence.
No consumer MAY infer executability, tradability, transaction readiness, or authority from a MarketObservation.
10.4 Public neutrality
The public contract MUST NOT expose:
the requested provider symbol;
the provider-returned symbol;
Registry mapping internals;
provider-specific payload fields;
provider-specific error objects;
raw Yahoo Chart data; or
legacy quote dictionaries.
Provider identity MAY appear only as normalized provenance where permitted by the existing provenance contract.
11. Invariants
The following invariants are mandatory:
The requested asset_id is the sole canonical subject.
Registry owns identity and provider-symbol custody, not market observations.
Market Intelligence owns MarketObservation.
Experience composition transfers no semantic ownership.
Providers remain witnesses and never establish canonical identity.
A provider symbol is boundary evidence and never platform identity.
Exactly one current configured provider mapping is required.
No fallback, guessing, transformation, routing, or successor substitution occurs.
Provider normalization occurs once under the existing canonical rules.
M39 introduces no second normalization path.
Missing evidence remains missing.
Receipt and cache time never become observation time.
Registry currency never fills missing provider currency.
MarketObservation remains non-execution evidence.
Observation retrieval is read-only and causes no Registry, portfolio, ledger, workspace, or transaction mutation.
Source degradation remains visible.
Unsupported and unavailable outcomes remain distinct.
A market-observation failure cannot block unrelated workspace content.
M31–M38 contracts remain unchanged.
The M38 reserved slot remains historically frozen.
12. Prohibited Behavior
M39 implementations and later work packages SHALL NOT:
parse a raw provider response outside the existing provider normalization boundary;
create an alternate canonicalization path from a legacy quote dictionary;
silently default missing provider evidence;
interpret a provider response as identity authority;
expose provider symbols as resource identity;
call Search or Resolver to recover a mapping;
query another provider after the configured provider fails;
treat provider timeout or malformed evidence as permanent noncoverage;
represent missing or ambiguous evidence as AVAILABLE;
expose execution evidence directly through the public resource;
convert a Market Observation into an execution input;
modify M32 evidence collection, classification, shadow behavior, or NO-GO status;
make an existing provider invalid merely because it lacks the new optional M39 capability;
add a required abstract provider operation;
change existing provider return types or error behavior;
alter existing /assets/{assetId} semantics;
mutate the M38 reserved-slot declaration or historical RESERVED state;
imply that declaration, catalog presence, enablement, health, and runtime binding are equivalent.
13. Compatibility Requirements
13.1 Frozen milestone compatibility
M39 MUST preserve all frozen M31–M38 contracts.
In particular:
M32 canonical execution planning remains NO-GO;
ExecutionQuoteEnvelope remains unchanged;
existing get_quote, history, fundamentals, news, and related provider contracts remain unchanged;
existing Yahoo Chart and legacy yfinance behavior remains unchanged;
M35 attachment classes remain unchanged;
M37 Search contracts remain unchanged;
M38 Workspace Context, Asset Focus, ProjectionEnvelope, ContributionDescriptor, ContributionAvailability, navigation, and Discovery Experience contracts remain unchanged;
existing HTTP routes retain their request, response, error, and ownership semantics.
13.2 Additive-only provider refinement
Any provider-interface refinement required by M39:
MUST be optional and additive;
MUST NOT add a required abstract operation;
MUST NOT alter an existing method’s signature, result, failure behavior, or semantic contract;
MUST NOT make an existing provider implementation non-conformant solely because it lacks M39 support;
MUST represent absent M39 support as UNSUPPORTED; and
MUST leave M32 behavior byte-for-byte and semantically unchanged.
A new optional capability contract MAY coexist with existing provider contracts. Its existence SHALL NOT promote or reinterpret an existing execution contract.
13.3 HTTP compatibility
The market-observation route is additive.
It MUST NOT:
redesign /assets/{assetId};
change existing authentication behavior;
change global HTTP error schemas;
shadow or redirect an existing route; or
change canonical asset reads to invoke providers.
14. Feature-Flag Expectations
M39 runtime exposure SHALL be default-off until the applicable later work package passes this specification’s conformance gate.
While disabled:
the M39 public surface and Experience attachment SHALL remain externally inactive;
no M39 provider request SHALL occur;
no M39 contribution SHALL be composed;
the M38 baseline SHALL remain observably unchanged;
disabled state SHALL NOT be reported as provider UNSUPPORTED; and
no schema, cache, Registry, or domain-data migration SHALL be required.
Activation MUST be explicit and reversible.
Feature state SHALL NOT alter the meaning, shape, ownership, provider derivation, or availability rules of the M39 contract.
The names, storage, and operational topology of feature controls are not defined by WP1.
15. Conformance Requirements
Conformance SHALL include objective proof of every requirement below.
Identifier	Required proof
OWN-01	Market Intelligence is the sole semantic owner of MarketObservation
OWN-02	Registry ownership is limited to asset identity, existence, and mapping custody
OWN-03	The /assets addressing path does not transfer observation ownership
HTTP-01	The resource accepts only exact canonical asset_id addressing
HTTP-02	Malformed and unknown identities fail under existing HTTP contracts without provider access
HTTP-03	The response subject always equals the requested asset_id
DER-01	The effective server-selected provider is the frozen yahoo_chart path, and the normalized path, PRICE_PROVIDER selection, and Registry yfinance namespace are not conflated
DER-02	The qualifying mapping value is passed unchanged
DER-03	Every prohibited fallback or transformation is rejected
DER-04	Zero qualifying mappings produce UNSUPPORTED; multiple or contradictory qualifying mappings produce integrity-qualified UNAVAILABLE; neither outcome causes provider access
OBS-01	MarketObservation contains only the fields and meanings permitted by §10, and contract_revision is the exact string "1"
OBS-02	Observation, receipt, and cache times remain distinct
OBS-03	Missing currency, time, session, and quality evidence remain absent
OBS-04	Provider-specific payload shapes do not cross the public boundary
SEP-01	MarketObservation is structurally distinct from execution evidence
SEP-02	A Market Observation cannot satisfy an execution input contract
SEP-03	No execution authority or executability can be inferred from the resource
NOR-01	Existing canonical normalization is reused
NOR-02	No raw-provider or legacy-dictionary alternate normalization path exists
AVL-01	Every availability condition matches §8.2 and every AVAILABLE result satisfies the explicit floor in §8.1
AVL-02	UNSUPPORTED is limited to the permanent capability conditions in §8.3
AVL-03	Transient and integrity failures remain UNAVAILABLE
AVL-04	Source availability remains distinct from ContributionAvailability
AVL-05	Required, expected-present, and conditionally applicable fields are classified according to §8.1
PROV-01	Provider-interface changes, if any, are optional and additive
PROV-02	Existing providers remain conformant without M39 support
COMP-01	Existing provider methods and results remain unchanged
COMP-02	M32 execution evidence and shadow behavior remain unchanged
COMP-03	Existing HTTP contracts remain unchanged
COMP-04	M35–M38 contracts remain unchanged
BIND-01	M39 declares a concrete contribution descriptor without redeclaring the M38 slot
BIND-02	The M39 binding contract references the frozen market slot separately
BIND-03	The M38 slot’s historical declaration and RESERVED state are not rewritten
FLAG-01	Default-off state performs no M39 provider I/O or composition
FLAG-02	Disabling M39 restores the pre-M39 observable surface
ROLL-01	Rollback requires no data, schema, Registry, ledger, or cache repair

Conformance evidence MUST demonstrate both positive behavior and prohibited-path rejection. Success-path evidence alone is insufficient.
16. Acceptance Criteria
M39-WP1 is accepted only when:
every normative field and concept has exactly one owner;
the public resource and its subject semantics are unambiguous;
the complete availability matrix is frozen;
the exact provider tuple and mapping-selection rules are frozen;
“no symbol fallback” requires no later interpretation;
UNSUPPORTED and UNAVAILABLE are objectively distinguishable;
the MarketObservation contract is structurally non-execution;
canonical normalization has exactly one authoritative path;
all provider refinements are constrained to additive-only compatibility;
M31–M38 behavior remains unchanged;
the M38 reserved slot and the M39 declaration and binding are clearly distinguished;
default-off and rollback expectations are explicit;
every conformance requirement has an objective proof obligation;
no later work package must make an architectural ownership, identity, availability, compatibility, or fallback decision.
Upon acceptance, this document SHALL be the sole M39-WP1 boundary authority.
17. Rollback Criteria
M39 SHALL be considered safely rollback-capable only if:
runtime activation can be disabled without changing persisted data;
disabling M39 causes no provider request or contribution composition;
existing M31–M38 behavior resumes without repair or translation;
no Registry record must be removed, restored, or rewritten;
no ledger, portfolio, workspace, or transaction data is affected;
no cache or schema migration must be reversed;
no existing provider contract must be restored; and
the frozen M38 reserved slot remains valid and unchanged.
Rollback SHALL NOT require reinterpretation of any previously recorded evidence.
18. Deferred Decisions
The following remain intentionally deferred and receive no authority from WP1:
provider ranking, routing, or fallback;
support for providers other than the frozen M39 v1 provider path;
client or workspace provider preference;
normalization-kernel extraction when such extraction could disturb M32;
historical, bulk, or streaming observation contracts;
persistent MarketObservation storage;
new cache or freshness policy;
cross-provider reconciliation;
FX or currency conversion;
execution adoption or transaction admission;
new observation kinds beyond the frozen contract;
feature-control names and deployment topology;
binding of any M38 slot other than the reserved market contribution;
Resolver, other Intelligence, intent, or action capabilities;
amendments to M31–M38 contracts.
These deferrals SHALL NOT be interpreted as implicit extension points within M39. Any future adoption requires its own approved authority.
