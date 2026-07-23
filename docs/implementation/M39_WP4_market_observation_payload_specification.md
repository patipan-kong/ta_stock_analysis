# M39-WP4 — Market Observation Payload Specification

**Status:** Canonical specification candidate for independent constitutional review

**Authority:** M39-WP4

**Nature:** Normative constitutional payload specification

## 1. Purpose

This specification defines the canonical semantic boundary of an Observation Payload.

An Observation Payload preserves the provider-neutral fact content of one Observation Event. It makes the represented claim understandable without importing provider packaging, implementation behavior, runtime state, transport semantics, storage structure, or analytical interpretation.

Payload answers:

> What provider-neutral fact content must be preserved so that this Observation Event continues to mean what its Observation Origin observed, measured, declared, published, or reported?

Payload does not answer:

- who or what qualifies as an Observation Source;
- who or what is responsible for the claim;
- what Canonical Observation Class applies;
- whether the claim is true, trusted, important, current, actionable, or suitable;
- how the claim is acquired, represented, transmitted, stored, exposed, or processed; or
- what any consumer should conclude or do.

This specification establishes semantic obligations only. It does not authorize implementation, provider integration, runtime adoption, persistence, transport, public exposure, or amendment of an existing contract.

## 2. Authority and Compatibility

This specification is subordinate to the Platform Architecture and preserves all ratified governance through M39-WP3.

In particular:

- M38 remains complete and frozen;
- the M38 reserved market contribution and all M38 envelope, attachment, composition, availability, and ownership contracts remain unchanged;
- M39-WP1 remains complete and frozen;
- the M39-WP1 `MarketObservation` contract, public boundary, availability model, exact provider derivation, canonical normalization reuse, feature expectations, and execution separation remain unchanged;
- M39-WP2 remains authoritative for Observation Source eligibility, Observation Event, Observation Payload, Observation Timestamp, and Observation Origin definitions, source boundaries, exclusions, provenance, and provider independence;
- M39-WP3 remains authoritative for the canonical Observation Classes, Classifying Fact, single-class rule, mixed-content treatment, and additive class admission;
- Market Intelligence remains the sole semantic owner of Market Observation and Observation Payload;
- Asset Foundation remains the sole owner of canonical asset identity and Registry adjudication;
- Connectivity & Ingestion retains ownership of external-fact ingestion toward ledger truth;
- all existing ledger, portfolio, decision, authorization, execution, provider, runtime, storage, analytics, Trust, and Experience boundaries remain unchanged; and
- Observation remains evidence, never identity authority, ledger truth, investment judgment, execution authority, or presentation authority.

This specification elaborates the conceptual Observation Payload already defined by M39-WP2. It SHALL NOT redefine that term, alter a class boundary established by M39-WP3, or widen the concrete M39-WP1 `MarketObservation` contract.

Nothing in this specification declares a payload field, schema, enum, wire token, serialization, container, object model, table, or public representation.

## 3. Scope

M39-WP4 defines:

- canonical provider-neutral payload principles;
- the semantic content an Observation Payload may preserve;
- minimum semantic sufficiency;
- payload and adjacent-domain boundaries;
- payload ownership;
- temporal and provenance preservation obligations;
- representation of source-reported uncertainty, absence, and qualification;
- semantic treatment of corrections, revisions, retractions, and later measurements;
- compatibility with M38 and M39-WP1 through M39-WP3;
- additive payload extensibility;
- constitutional invariants;
- prohibited interpretations;
- informative examples; and
- objective conformance criteria.

M39-WP4 does not define:

- implementation representation;
- an API, endpoint, request, response, or public contract;
- a provider interface, provider mapping, adapter, capability, or integration;
- runtime dispatch, routing, scheduling, orchestration, retry, fallback, or failover;
- transport, protocol, serialization, file format, event bus, queue, or message shape;
- storage, persistence, database, caching, indexing, retention, or replay;
- authentication, authorization, tenancy, approval, or permissions;
- analytics, calculations, derived indicators, predictions, recommendations, or strategies;
- execution, orders, transactions, portfolios, ledger behavior, or accounting;
- Experience composition, alert, watchlist, screener, or user-interface behavior; or
- implementation or public exposure of any Observation Class.

## 4. Canonical Vocabulary

### 4.1 Observation Payload

An **Observation Payload** is the canonical, provider-neutral fact content carried by one Observation Event.

It preserves what the Observation Origin observed, measured, declared, published, or reported, together with every source-established qualification necessary to retain that meaning.

An Observation Payload:

- MUST express one Classifying Fact at the semantic granularity required by M39-WP3;
- MUST use platform-owned semantic vocabulary;
- MUST preserve material source meaning without embellishment or omission;
- MUST remain attributable to the Observation Event and its Observation Origin under M39-WP2;
- MUST preserve material temporal, provenance, uncertainty, absence, and lifecycle qualifications under this specification;
- MUST NOT contain provider packaging or implementation semantics;
- MUST NOT add platform calculation, inference, judgment, authority, or action; and
- MUST NOT transfer ownership from any adjacent constitutional domain.

The Observation Payload is conceptual. This definition does not prescribe where semantic content is placed in any representation.

### 4.2 Payload Meaning

**Payload Meaning** is the provider-neutral interpretation of the External Fact or Source-Reported Claim preserved by an Observation Payload.

Payload Meaning includes the distinctions necessary to understand what was asserted and under what source-established conditions. It excludes the mechanics by which the assertion was acquired, encoded, stored, delivered, or displayed.

Equivalent source claims MUST have equivalent Payload Meaning even when their provider fields, labels, packaging, transports, or implementations differ.

### 4.3 Claim Content

**Claim Content** is the source-reported substance of the one Classifying Fact represented by the Observation Event.

Depending on the Canonical Observation Class, Claim Content may consist of a measured value, a declared term, a published statement, a status, an occurrence, or another externally observable assertion admitted by M39-WP2 and M39-WP3.

Claim Content MUST NOT include an analytical conclusion, platform calculation, prediction, recommendation, strategy, or action instruction merely because it appears near qualifying evidence in a source artifact.

### 4.4 Semantic Qualifier

A **Semantic Qualifier** is source-established context without which Claim Content would be materially ambiguous or misleading.

Examples of qualifier meaning include:

- the unit, currency, scale, basis, or measurement dimension of a value;
- whether a value is preliminary, estimated, approximate, final, corrected, or source-disputed;
- the scope, period, market state, event status, or applicability declared by the source; and
- an explicit limitation or caveat attached to the claim.

A Semantic Qualifier preserves source meaning. It MUST NOT become a platform quality score, analytical interpretation, or implementation flag.

### 4.5 Semantic Subject

The **Semantic Subject** is the entity, instrument, venue, jurisdiction, period, publication, event, or externally scoped phenomenon about which the Source-Reported Claim is made.

A Semantic Subject:

- MUST be preserved at the specificity established by the source and prior governance;
- MAY reference an existing canonical identity where that reference is already governed;
- MUST NOT mint, merge, infer, replace, or adjudicate canonical identity;
- MUST NOT be silently broadened or narrowed; and
- MUST remain distinct from the Observation Origin and any relay.

Where M39-WP1 applies, its frozen `subject_asset_id` ownership and subject-preservation rules remain exact and unchanged.

### 4.6 Semantic Sufficiency

**Semantic Sufficiency** is the condition in which the canonical fact content preserves enough source-established meaning for an independent reader to understand the represented claim using governed platform vocabulary, without consulting provider-private semantics or inventing missing evidence.

Semantic Sufficiency is class-relative. The material distinctions required for one Canonical Observation Class need not be the same as those required for another.

Semantic Sufficiency:

- requires preservation of every material qualification actually established by the source;
- does not require copying an entire source artifact;
- does not require content excluded by M39-WP2 or M39-WP3;
- does not require a value that the source did not establish;
- does not imply truth, quality, availability, freshness, completeness for a consumer, or fitness for use; and
- does not define structural field presence.

### 4.7 Semantic Absence

**Semantic Absence** is the explicit preservation of a material fact that the source did not establish, did not supply, withheld, marked unknown, marked not applicable, or otherwise qualified as absent.

These meanings MUST remain distinct when the source distinguishes them. Semantic Absence MUST NOT be replaced with a default, estimate, inferred convention, empty value of unclear meaning, or value taken from another source.

### 4.8 Payload Fidelity

**Payload Fidelity** is the preservation of Payload Meaning without semantic addition, loss, substitution, or reinterpretation.

Representation-preserving canonical normalization MAY express equivalent source meaning in existing platform-owned vocabulary. It MUST NOT aggregate, calculate, smooth, rank, score, infer, forecast, endorse, or otherwise change the claim.

### 4.9 Correction Lineage

**Correction Lineage** is the semantic relationship by which a new Observation Event states that it corrects, revises, retracts, replaces, or otherwise qualifies an earlier source claim.

Correction Lineage:

- MUST preserve the lifecycle relationship asserted by the source;
- MUST distinguish the new event from the earlier event;
- MUST NOT mutate the earlier event or its Payload Meaning;
- MUST NOT imply that the platform has independently adjudicated truth; and
- does not prescribe identifiers, links, storage, versioning, ordering, or retrieval behavior.

### 4.10 Payload Compatibility

**Payload Compatibility** is the property that provider replacement, runtime change, transport change, storage change, or additive extension does not alter existing Payload Meaning, ownership, or consumer obligations.

Payload Compatibility is semantic. It does not define binary, source, wire, schema, or deployment compatibility.

## 5. Payload Principles

### 5.1 Semantic-first

Payload MUST be defined from the meaning of the represented external fact or source-reported claim.

Provider field names, documents, endpoints, product labels, SDK types, transport messages, database records, or display layouts MUST NOT define canonical payload meaning.

### 5.2 Provider-neutral

The same source claim MUST retain the same Payload Meaning when supplied through different qualifying sources or relays.

A concrete origin or relay identity MAY remain provenance under M39-WP2. Its identity MUST NOT cause otherwise equivalent Claim Content to acquire different semantics.

### 5.3 One-fact responsibility

One Observation Payload MUST preserve the Claim Content of exactly one Observation Event and one Classifying Fact.

A source artifact containing independently meaningful facts MUST be separated according to M39-WP3 or remain unadmitted in that form. Payload MUST NOT be used to evade the single-class rule by embedding multiple independently classified facts into one event.

### 5.4 Faithful, not authoritative

Payload MUST faithfully represent the attributable source claim.

Faithful representation does not declare the claim to be:

- canonical identity;
- ledger or accounting truth;
- verified fact;
- high quality;
- analytically important;
- suitable for a portfolio;
- executable or tradable;
- a recommendation; or
- authority to act.

### 5.5 Complete without fabrication

Payload MUST preserve all material meaning established by the source and MUST preserve material absence when the source does not establish a value.

Semantic completeness SHALL NOT justify:

- inventing a missing value;
- inferring an unstated unit, currency, time, status, or subject;
- filling evidence from Registry, portfolio, workspace, a local clock, market convention, another observation, or another provider;
- converting a source claim into a platform calculation; or
- adopting excluded material from the surrounding source artifact.

### 5.6 Deterministic

Given the same source claim, the same Canonical Observation Class, and the same governed semantic vocabulary, independent conforming reviews MUST identify the same material Claim Content and qualifications.

Where source meaning is too ambiguous to satisfy that rule, the candidate MUST remain unadmitted until its meaning is resolved under existing governance.

### 5.7 Reproducible

Payload Meaning MUST be reproducible from canonical fact content and its governed semantic associations without consulting:

- a live provider;
- current provider documentation;
- provider-specific code;
- a transport session;
- mutable runtime state;
- a cache;
- a storage layout; or
- a current analytical model.

This principle does not require persistence or historical replay.

### 5.8 Immutable in meaning

Once an Observation Event is represented, its Payload Meaning MUST NOT change.

Later validation, correction, revision, retraction, receipt, retrieval, storage, presentation, or analysis SHALL NOT retroactively alter what that event represented the source as having claimed.

### 5.9 Ownership-preserving

Payload MAY reference concepts owned by adjacent domains only within their existing constitutional contracts. Reference MUST NOT transfer ownership, create shared authority, or permit Observation to adjudicate those concepts.

### 5.10 Additive

Future payload semantics MUST be admitted additively under §14. Existing Payload Meaning MUST NOT be renamed, narrowed, widened, superseded, or reinterpreted by an extension.

## 6. Canonical Payload Semantics

### 6.1 Minimum semantic obligations

Every admitted Observation Payload MUST preserve:

1. the Claim Content of one qualifying External Fact or Source-Reported Claim;
2. the meaning and scope of the Semantic Subject;
3. every source-established unit, currency, scale, basis, status, period, dimension, or other qualifier material to interpreting the claim;
4. every material source-reported uncertainty, limitation, absence, or qualification;
5. the distinction among independently meaningful temporal claims under §10;
6. the semantic provenance required by §11;
7. correction, revision, retraction, or later-measurement meaning when applicable under §13; and
8. enough provider-neutral meaning to satisfy Semantic Sufficiency.

These are semantic obligations, not fields or structural components.

### 6.2 Class-relative content

The Canonical Observation Class determines which kind of fact the payload may preserve. It does not by itself supply the Claim Content.

Accordingly:

- a class name MUST NOT substitute for the actual source claim;
- payload content MUST remain inside the semantic boundary of its one M39-WP3 class;
- payload MUST NOT add content belonging to another class merely because it appeared in the same artifact;
- class-specific material qualifiers MUST remain explicit; and
- an event whose content cannot satisfy exactly one class and Semantic Sufficiency MUST remain unadmitted.

This specification does not define class-specific payload profiles or authorize any class for implementation.

### 6.3 Values and declared terms

When Claim Content includes a value or declared term, its material meaning MUST be preserved.

Material meaning MAY include, when source-established:

- value type and measurement dimension;
- unit, currency, scale, or basis;
- range, bound, ratio, rate, or directionality;
- declared status or applicability;
- reference period or effective condition; and
- precision or approximation.

A bare number, code, label, or text fragment whose provider-neutral meaning cannot be established is not semantically sufficient.

Canonical preservation MUST NOT recompute, convert, aggregate, interpolate, extrapolate, or otherwise derive a replacement value.

### 6.4 Statements and publications

When Claim Content is a publication event or attributable statement, payload MAY preserve only the eligible fact-bearing content admitted by M39-WP2 and M39-WP3.

Payload MUST distinguish:

- the externally observable fact that content was published;
- an independently qualifying fact reported within that content; and
- excluded prediction, recommendation, strategy, analysis, or action language.

The fact of publication MUST NOT cause prohibited content to become canonical Observation meaning. Independently qualifying facts MUST be separated at their governed semantic granularity.

### 6.5 Status and occurrence

When Claim Content is a status or occurrence, payload MUST preserve:

- what status or occurrence the source reported;
- the subject and scope to which it applies;
- any source-established effective or occurrence time;
- any material condition or qualification; and
- whether the source described an announcement, an expected effective state, or an observed state.

A source-declared future effective date is an externally observable declaration. Preserving that declaration does not convert it into a platform prediction. Payload MUST NOT assert that the future state actually occurred unless a qualifying source claim establishes that separate fact.

### 6.6 Subject references

Payload MAY preserve a reference to a subject only when the reference is meaningful under prior governance.

Payload MUST NOT:

- create a canonical subject identity;
- infer identity from a symbol, name, provider code, or provider-returned text;
- replace one subject with a related, predecessor, successor, or fallback subject;
- treat a provider identifier as canonical identity;
- adjudicate identity disagreement; or
- amend Registry classification or lifecycle.

An unresolved or externally scoped subject claim MAY remain attributable source evidence only where M39-WP2 and the applicable class boundary permit it. It MUST NOT be presented as canonical Registry identity.

### 6.7 Context without derivation

Source-established context MAY be preserved when omission would materially change the claim.

Context MUST NOT be used to import:

- platform calculations;
- analytical features or derived indicators;
- quality or trust verdicts;
- portfolio meaning;
- recommendations or strategies;
- execution eligibility or action authority;
- provider packaging; or
- unrelated content from the source artifact.

### 6.8 Canonical normalization

Representation-preserving normalization MUST reuse existing canonical normalization vocabulary where prior governance provides it.

Payload SHALL NOT create a duplicate canonical vocabulary, competing normalization path, or provider-private extension.

Normalization MUST preserve source meaning and MUST NOT:

- manufacture evidence;
- collapse materially distinct meanings;
- erase uncertainty or absence;
- convert operational metadata into observation semantics;
- change Observation Classification;
- change the Semantic Subject;
- transform observation evidence into execution evidence; or
- make a source claim authoritative.

This section defines a semantic constraint only. It does not define mappings, adapters, algorithms, precedence, or runtime behavior.

## 7. Payload Boundaries and Boundary Matrix

| Boundary question | Inside Observation Payload | Outside Observation Payload | Required resolution |
| --- | --- | --- | --- |
| What did the source claim? | One provider-neutral Classifying Fact and its material source qualifications | Provider artifact, packaging, or unrelated surrounding content | Preserve only eligible canonical fact meaning |
| What is the claim about? | Source-established Semantic Subject or an already-governed identity reference | Identity minting, merging, inference, substitution, or adjudication | Preserve reference without acquiring Asset Foundation authority |
| What does a value mean? | Source-established value meaning, unit, currency, scale, basis, scope, and qualification | Conversion, aggregation, interpolation, calculation, or inferred defaults | Preserve supplied meaning; leave missing meaning absent |
| When does the claim apply? | Distinct source-established observation, occurrence, effective, reference-period, or publication meaning | Receipt, retrieval, cache, storage, schedule, display, or local-clock substitution | Preserve temporal meanings without collapse |
| Who is responsible for the claim? | Semantic association to Observation Origin and material relay role | Provider routing or vendor-dependent interpretation | Preserve provenance under M39-WP2 |
| How certain is the source? | Attributed source-reported uncertainty, range, provisional status, dispute, or limitation | Platform confidence, trust score, truth verdict, or inferred probability | Preserve testimony; assessment remains with its existing owner |
| What is missing? | Explicit source-established absence, unknown, withheld, or not-applicable meaning | Fabricated value, silent default, or ambiguous empty placeholder | Preserve the exact absence meaning |
| Is this a correction? | New Claim Content and source-established Correction Lineage | Mutation, overwrite, silent replacement, or platform truth adjudication | Preserve both event meanings |
| Is the claim true or useful? | Nothing beyond faithful source testimony | Validation, ranking, quality scoring, importance, suitability, or analytical conclusion | Existing Trust, Analytics, Decision, and consumer owners retain authority |
| What should happen next? | Nothing | Alert, recommendation, strategy, order, execution, transaction, or workflow | Action and operational domains retain authority |
| How is payload represented? | No constitutional representation choice | Field layout, object, schema, enum, JSON, serialization, table, message, or UI | Govern separately without changing payload meaning |
| How is payload moved or retained? | No transport or persistence behavior | Protocol, adapter, queue, event bus, database, cache, retention, or replay | Operational owners retain responsibility |

## 8. Ownership Model

Every concept has exactly one semantic owner. Reference, attribution, normalization, relay, custody, consumption, or presentation does not create shared ownership.

| Concept or boundary | Canonical owner | Payload relationship |
| --- | --- | --- |
| Observation Payload and Payload Meaning | Market Intelligence | Sole semantic ownership under this specification |
| Observation Source, Event, Timestamp, and Origin semantics | Market Intelligence under M39-WP2 | Remain unchanged and constrain payload eligibility and attribution |
| Observation Classification | Market Intelligence under M39-WP3 | Defines the one kind of fact whose content payload preserves |
| External source claim authorship | Observation Origin under M39-WP2 | Origin authors the claim but does not own the platform’s canonical payload vocabulary or downstream verdict |
| Canonical asset identity and Registry adjudication | Asset Foundation | Payload may reference governed identity but cannot create, infer, merge, replace, classify, or adjudicate it |
| External-fact ingestion toward ledger truth | Connectivity & Ingestion | Payload evidence does not create an ingestion proposal, reconciliation result, or truth-path authority |
| Transactions and financial truth | Ledger & Accounting | Observation Payload cannot create, amend, validate, or supersede ledger facts |
| Portfolio derivations | Portfolio Intelligence | Portfolio meaning calculated from observations remains outside payload |
| Analytics and derived results | The constitutional owner of each derived result | Calculations and interpretations do not become Observation Payload |
| Investment conclusions and actions | Decision Intelligence and existing frozen action boundaries | Prediction, recommendation, strategy, intent, approval, and execution remain outside payload |
| Trust and quality assessment | Trust & Evaluation | Assessment may reference payload but cannot rewrite its source-reported meaning |
| Authentication, authorization, approval, and human authority | Existing non-domain authority boundaries | Payload supplies no identity proof, permission, delegation, approval, or authority |
| Provider translation and witness interaction | Existing Market Data provider boundary | Provider-specific translation does not own canonical Payload Meaning |
| Runtime and orchestration | Existing runtime and operational owners | Invocation, sequencing, retry, or failover does not own or alter Payload Meaning |
| Transport and storage | Existing infrastructure owners | Delivery and custody preserve representations without acquiring semantic ownership |
| Experience composition | Experience Platform | Rendering and composition do not define or alter Payload Meaning |

No row grants new authority. Every prior owner retains its complete frozen boundary.

## 9. Relationship to Source and Classification

M39-WP2, M39-WP3, and M39-WP4 answer independent constitutional questions:

| Dimension | Governing question | Governing authority | Must not determine |
| --- | --- | --- | --- |
| Observation Source | What kind of external witness can supply a qualifying claim? | M39-WP2 | Payload meaning or Observation Class |
| Observation Origin | Who or what is responsible for the claim? | M39-WP2 | Payload meaning by identity alone |
| Observation Classification | What kind of fact does the event represent? | M39-WP3 | Source eligibility, provider selection, or representation |
| Observation Payload | What provider-neutral fact content preserves the claim? | M39-WP4 within M39-WP2 and M39-WP3 constraints | Source eligibility, class admission, provider behavior, or implementation |

The dimensions are associated but non-substitutable:

- an eligible source does not make every output an eligible payload;
- a source or origin identity does not define Payload Meaning;
- payload content does not qualify an otherwise ineligible source;
- payload content MUST remain inside exactly one class boundary;
- a class label does not supply semantically sufficient Claim Content;
- semantically sufficient payload does not select or authorize a provider;
- multiple sources MAY report equivalent payload meaning without changing the class;
- one source MAY report events with different payload meanings and different classes; and
- a new payload meaning MUST NOT enter through a provider-private label or an `OTHER` or `UNKNOWN` class.

Payload preserves provenance without turning provenance into semantic branching. Payload preserves classification without turning classification into implementation dispatch.

## 10. Temporal Preservation

### 10.1 Temporal meaning

Every material source-established temporal claim MUST retain explicit meaning.

Depending on the Canonical Observation Class, temporal meaning MAY include:

- when a state was observed;
- when an occurrence happened;
- when a publication was issued;
- when declared terms become or became effective;
- the period, interval, or as-of boundary to which a measurement applies;
- when a source-reported status began, ended, or was expected to apply; and
- when a correction, revision, or retraction was issued.

This list is semantic and non-exhaustive. It does not define timestamp fields.

### 10.2 Distinct temporal claims

Materially distinct temporal claims MUST remain distinct.

In particular:

- observation time MUST NOT be replaced by receipt time;
- observation time MUST NOT be replaced by retrieval, cache, storage, schedule, display, or local-clock time;
- publication time MUST NOT be treated as occurrence or effective time unless the source establishes that equivalence;
- a reference period MUST NOT be collapsed into a publication instant;
- an announced effective time MUST NOT be treated as proof that the announced event occurred; and
- a correction issue time MUST NOT replace the temporal meaning of the fact being corrected.

### 10.3 Precision and qualification

Source-established temporal precision and qualification MUST be preserved.

A date-only claim MUST NOT be fabricated into an exact instant. An approximate time MUST remain approximate. An interval MUST NOT be collapsed to one endpoint when doing so changes meaning. An unstated time basis MUST remain absent or explicitly unresolved rather than being inferred from locale, market convention, runtime configuration, or a consumer clock.

### 10.4 Operational times

Receipt, retrieval, cache, storage, scheduling, and display times MAY exist under prior governance as provenance or operational context.

They:

- MUST remain distinguishable from Observation Timestamp meaning;
- MUST NOT manufacture a missing source-established time;
- MUST NOT change Claim Content or Observation Classification; and
- MUST NOT become evidence of freshness, occurrence, or effectiveness without separately governed meaning.

M39-WP1’s exact distinction among `observed_at`, `received_at`, and `cached_at` remains unchanged.

## 11. Provenance Preservation

### 11.1 Required semantic provenance

Every Observation Event MUST preserve enough semantic provenance to distinguish:

- the Observation Origin responsible for the Source-Reported Claim;
- any materially relevant relay role;
- the distinction between origin, relay, subject, and platform recipient;
- the source-established temporal meaning;
- material source-reported uncertainty, absence, or qualification; and
- correction, revision, retraction, or later-measurement status when applicable.

These obligations do not prescribe a provenance structure or field set.

### 11.2 Origin and relay

Origin and relay MUST remain distinct when the distinction is material to attribution.

A relay MUST NOT silently become the author of an originated claim. An origin MUST NOT be replaced by an adapter, SDK, protocol, file, cache, database, or platform component.

A concrete origin or relay identity MAY be retained as provenance. That identity:

- MUST NOT define the Canonical Observation Class;
- MUST NOT change otherwise equivalent Payload Meaning;
- MUST NOT establish identity, quality, truth, freshness, or authority;
- MUST NOT require provider-private vocabulary to interpret the claim; and
- MUST NOT cause consumers to branch semantically by vendor identity.

### 11.3 Method and basis qualification

When an origin explicitly qualifies a measurement by a methodology, basis, sample, scope, or declared limitation and that qualification is material to interpreting the claim, the qualification MUST be preserved at provider-neutral semantic meaning.

Observation MUST NOT:

- reproduce or execute the external methodology;
- infer an unstated methodology;
- endorse the methodology;
- convert the methodology into platform analytics; or
- retain an opaque provider code as though it were canonical meaning.

### 11.4 Reproducibility

Semantic provenance MUST be sufficient to preserve attribution and claim meaning independently of a provider’s current availability or documentation.

Reproducibility does not require this specification to define source-document retention, raw-payload retention, storage, replay, audit logging, or retrieval.

## 12. Uncertainty, Absence, and Qualification

### 12.1 Source-reported uncertainty

Payload MUST preserve material uncertainty expressly reported by the source.

Source-reported uncertainty MAY include:

- an estimated, preliminary, provisional, approximate, or final status;
- a range, bound, tolerance, confidence expression, or precision qualification;
- an explicit dispute, conflict, incompleteness, or limitation;
- an unknown, withheld, unavailable, or not-applicable value; and
- a source-declared dependency or condition.

Only meaning established by the source may be preserved as source-reported uncertainty.

### 12.2 No manufactured certainty

Observation MUST NOT:

- convert an estimate into an exact fact;
- select a midpoint or preferred value from a range;
- remove a provisional or disputed status;
- translate missing evidence into zero, false, empty text, or another apparently known value;
- infer confidence from provider reputation, availability, redundancy, or agreement;
- assign a platform confidence score;
- treat absence of a warning as proof of certainty; or
- treat Semantic Sufficiency as proof that the claim is correct.

### 12.3 Distinct absence meanings

When established by the source, the following meanings MUST remain distinct:

- not supplied;
- unknown;
- unavailable;
- withheld;
- not applicable;
- not yet established;
- explicitly none; and
- present but qualified.

This specification does not create tokens or representations for those meanings. It requires only that canonicalization not collapse materially different source meaning.

### 12.4 Platform assessment

Trust & Evaluation or another frozen owner MAY assess source quality, consistency, credibility, or correctness.

Such assessment:

- MUST remain distinct from source-reported uncertainty;
- MUST NOT rewrite the Observation Payload;
- MUST NOT change Observation Classification;
- MUST NOT retroactively alter the source claim; and
- MUST NOT be represented as though the Observation Origin supplied it.

### 12.5 Disagreement

Different origins reporting different claims do not authorize payload merger, averaging, precedence, or silent selection.

Each qualifying event MUST retain its own Claim Content, attribution, temporal meaning, and uncertainty. Reconciliation, trust assessment, or downstream selection belongs to its existing constitutional owner.

## 13. Corrections, Revisions, Retractions, and Later Measurements

### 13.1 New-event rule

A correction, revision, retraction, or later measurement is a new Observation Event under M39-WP2.

The new event:

- MUST preserve its own Claim Content;
- MUST retain its own temporal meaning and provenance;
- MUST preserve the lifecycle assertion made by the source;
- MUST preserve Correction Lineage when the source establishes the relationship;
- MUST receive the class required by M39-WP3; and
- MUST NOT mutate the earlier event or its Payload Meaning.

### 13.2 Classification stability

Correction lifecycle alone SHALL NOT create a separate class.

A correction, revision, or retraction MUST be classified according to the kind of fact it corrects, revises, retracts, or newly reports. The earlier event’s classification MUST NOT change.

### 13.3 Lineage fidelity

Correction Lineage MUST distinguish, where source-established:

- correction of an erroneous prior claim;
- revision of a previously published measurement or term;
- retraction or withdrawal of a prior claim;
- supersession declared by the origin; and
- a later independent measurement that does not correct the earlier event.

A later event MUST NOT be labeled a correction, revision, retraction, or supersession solely because its value differs.

### 13.4 No silent replacement

Payload semantics MUST NOT authorize:

- overwriting an earlier claim;
- presenting a revised value as though it were the only historical claim;
- erasing earlier uncertainty or qualification;
- merging two event meanings into one mutable payload;
- inferring a correction relationship not established by the source; or
- treating “latest,” “current,” “preferred,” or “effective” selection as intrinsic payload meaning unless the source claim itself establishes that meaning.

Selection of a current projection, version, or preferred evidence is outside this constitutional payload boundary.

### 13.5 Retraction

A retraction preserves the externally observable fact that the origin withdrew or disavowed an earlier claim. It does not retroactively make the earlier Observation Event nonexistent.

Observation MUST NOT infer the replacement truth, legal consequence, portfolio consequence, or required action from the retraction.

## 14. Compatibility and Additive Extensibility

### 14.1 Frozen compatibility

M39-WP4 MUST remain compatible with:

- M38 projection and contribution governance;
- M39-WP1 public resource, concrete `MarketObservation` contract, exact initial `contract_revision`, field-presence rules, availability states, provider derivation, no-fallback rules, feature expectations, and rollback contract;
- M39-WP2 source qualification, event immutability, payload definition, temporal semantics, origin semantics, exclusions, ownership, provider independence, and reproducibility;
- M39-WP3 canonical class names, semantic boundaries, exactly-one-class rule, mixed-content treatment, correction classification, and extension rules; and
- every frozen identity, ingestion, ledger, portfolio, decision, Trust, authorization, execution, provider, runtime, storage, analytics, and Experience boundary.

No general concept in this specification overrides a more specific frozen contract.

### 14.2 M39-WP1 relationship

The M39-WP1 `MarketObservation` contract is one frozen concrete contract for the M39-WP1 Market Price boundary.

This specification:

- MUST NOT add, remove, rename, reinterpret, or change the presence of any M39-WP1 field;
- MUST NOT change the exact initial `contract_revision` value;
- MUST NOT redefine `price`, `price_kind`, `currency`, `observed_at`, `received_at`, `cached_at`, `market_session`, `provenance`, `quality_context`, or `warnings`;
- MUST NOT turn `price_kind` into an Observation Classification field;
- MUST NOT change AVAILABLE, DEGRADED, UNAVAILABLE, or UNSUPPORTED semantics;
- MUST NOT change provider request derivation or the no-symbol-fallback rule;
- MUST NOT expose provider-specific payload content; and
- MUST NOT make M39-WP1 assignment-compatible with execution evidence.

The broader constitutional vocabulary in M39-WP4 does not imply that any additional content is present in, required by, or permitted through M39-WP1.

### 14.3 Additive extension test

A future payload-semantic extension MAY be admitted only through separately approved governance and only when all of the following are established:

1. The proposed meaning belongs to an Observation Event admitted by M39-WP2.
2. The event has exactly one class under M39-WP3 or a separately approved additive class.
3. The meaning is necessary to preserve a source-established fact or material qualification.
4. The meaning is provider-neutral and implementation-neutral.
5. The meaning is not already represented by existing canonical vocabulary.
6. The meaning is semantically distinct and non-conflicting.
7. Its temporal, provenance, uncertainty, absence, and correction semantics are explicit where applicable.
8. It preserves every existing ownership boundary.
9. It introduces no calculation, analytics, prediction, recommendation, strategy, portfolio meaning, execution, transaction, or authority.
10. Existing Payload Meaning and existing consumer obligations remain unchanged.
11. No provider, transport, storage, runtime, API, schema, or serialization is required to explain it.
12. It receives separate authority before implementation or public exposure.

### 14.4 Extension prohibitions

A future extension MUST NOT:

- reinterpret, narrow, widen, rename, alias, supersede, or invalidate existing Payload Meaning;
- change an existing Observation Class or reclassify an existing event;
- enter through a provider-private field, label, code, or opaque extension;
- create an `OTHER`, `UNKNOWN`, or generic payload escape hatch;
- make a concrete provider, relay, protocol, format, runtime, or storage system mandatory;
- require existing consumers to understand the extension to preserve their current behavior;
- turn provenance into semantic branching;
- convert source testimony into identity, ledger, analytical, decision, or action authority;
- widen M39-WP1 implicitly; or
- reopen M38 or M39-WP1 through M39-WP3.

Provider support for existing Payload Meaning is an implementation concern, not a constitutional extension.

## 15. Constitutional Invariants

The following rules are normative and cumulative.

### Semantic fidelity and sufficiency

- **OP-01:** Every Observation Payload MUST preserve the provider-neutral Claim Content of exactly one Observation Event.
- **OP-02:** Every Observation Payload MUST remain within exactly one M39-WP3 Canonical Observation Class.
- **OP-03:** Payload MUST preserve every source-established qualification material to understanding the claim.
- **OP-04:** Payload MUST preserve material absence and MUST NOT fabricate, default, infer, or substitute missing evidence.
- **OP-05:** Canonical payload meaning MUST be reproducible without a live provider, provider-private documentation, or mutable runtime state.
- **OP-06:** Equivalent source claims under the same governed vocabulary MUST retain equivalent Payload Meaning.
- **OP-07:** Ambiguous or opaque content that cannot satisfy Semantic Sufficiency MUST remain unadmitted.

### Provider and implementation neutrality

- **OP-08:** Payload semantics MUST be provider-neutral, runtime-neutral, transport-neutral, storage-neutral, serialization-neutral, and implementation-neutral.
- **OP-09:** Provider products, SDK types, field names, endpoints, protocols, formats, database structures, and runtime behavior MUST NOT enter canonical payload vocabulary.
- **OP-10:** Concrete origin or relay identity MAY remain provenance but MUST NOT determine Payload Meaning or Observation Classification.
- **OP-11:** Representation-preserving normalization MUST reuse existing canonical vocabulary and MUST NOT create a duplicate normalization path.
- **OP-12:** This specification MUST NOT define fields, schemas, enums, wire tokens, APIs, serialization, storage, transport, or implementation.

### Temporal and provenance integrity

- **OP-13:** Every material source-established temporal claim MUST retain explicit and distinct meaning.
- **OP-14:** Observation time MUST NOT be replaced by receipt, retrieval, cache, storage, schedule, display, or local-clock time.
- **OP-15:** Temporal precision, interval, and qualification MUST NOT be silently strengthened, weakened, or collapsed.
- **OP-16:** Observation Origin and materially relevant relay roles MUST remain attributable and distinct.
- **OP-17:** Provenance MUST NOT substitute for Claim Content, classification, identity, quality, truth, freshness, or authority.

### Uncertainty and lifecycle integrity

- **OP-18:** Material source-reported uncertainty, qualification, dispute, and absence MUST remain explicit.
- **OP-19:** Source-reported uncertainty MUST remain distinct from platform trust, quality, or correctness assessment.
- **OP-20:** Corrections, revisions, retractions, and later measurements MUST be new Observation Events and MUST NOT mutate earlier Payload Meaning.
- **OP-21:** Correction Lineage MUST reflect only a relationship established by the source and MUST NOT be inferred from differing values alone.
- **OP-22:** Correction lifecycle MUST NOT create a new Observation Class or change the earlier event’s class.

### Separation of concerns and ownership

- **OP-23:** Market Intelligence MUST remain the sole semantic owner of Observation Payload.
- **OP-24:** Payload MUST NOT transfer identity, Registry, ingestion, ledger, portfolio, decision, Trust, authorization, execution, provider, runtime, storage, analytics, or Experience authority.
- **OP-25:** Payload MUST NOT calculate, aggregate, convert, interpolate, infer, predict, recommend, strategize, authorize, trade, execute, transact, or evaluate a portfolio.
- **OP-26:** Consumption, relay, normalization, custody, rendering, or assessment MUST NOT transfer payload ownership or alter Payload Meaning.
- **OP-27:** Observation Payload MUST remain evidence and MUST NOT become canonical identity, ledger truth, judgment, suitability, or authority to act.

### Stability and forward compatibility

- **OP-28:** Once represented, an Observation Event’s Payload Meaning MUST remain immutable.
- **OP-29:** Future payload-semantic extensions MUST be additive and MUST preserve all existing meanings and consumer obligations.
- **OP-30:** A future extension MUST NOT enter through provider-private or catch-all vocabulary.
- **OP-31:** M38 and M39-WP1 through M39-WP3 MUST remain unchanged.
- **OP-32:** No payload principle or example SHALL imply implementation, runtime, provider, storage, transport, API, or public-exposure authority.

## 16. Prohibited Interpretation

This specification SHALL NOT be interpreted to:

- define or require a generic payload container;
- add a field to any existing or future contract;
- define a schema, enum, wire token, serialization, JSON shape, table, object, document, message, event bus, queue, or file;
- define an API, endpoint, request, response, status, or error;
- define provider mappings, adapters, interfaces, capability declarations, routing, fallback, or failover;
- define runtime branching, scheduling, orchestration, retry, caching, persistence, retention, replay, or transport;
- authorize implementation or public exposure of any Observation Class;
- copy raw provider payloads into canonical semantics;
- use provider identity or field names as payload meaning;
- treat an entire source artifact as one Observation Payload;
- bypass the M39-WP3 one-fact and one-class rules;
- treat a class name as sufficient Claim Content;
- treat source-reported content as verified truth;
- infer identity, currency, unit, time, status, uncertainty, or correction lineage;
- fill missing evidence from another source or adjacent domain;
- calculate, normalize by derivation, convert, aggregate, rank, score, predict, recommend, or strategize;
- define execution eligibility, portfolio value, transaction meaning, or action authority;
- mutate an earlier event when a correction, revision, retraction, or later measurement arrives;
- treat “latest” or “current” selection as a payload responsibility;
- widen the M39-WP1 `MarketObservation` contract;
- redefine M39-WP2 source or event eligibility;
- redefine an M39-WP3 class boundary; or
- reopen or amend a completed milestone.

No informative example creates an exception to a normative boundary.

## 17. Informative Examples

This section is informative. The normative rules remain in §§4–16.

### 17.1 Valid payload meaning

| Source-reported fact | Valid semantic preservation | Why it conforms |
| --- | --- | --- |
| A venue reports a closing value in a stated currency at a stated observation time | The observed value, price meaning, currency, observation time, subject, origin, and applicable qualifications | The content preserves one Market Price fact without execution meaning |
| An issuer declares a dividend with amount, currency, ex-date, record date, and payment date | Each declared term retains its label, subject, origin, and temporal meaning | Declared terms remain source evidence and distinct dates are not collapsed |
| An issuer announces a reverse split effective on a future date | The announced ratio, announced effective date, subject, publication attribution, and announcement status | A future effective declaration is preserved without asserting completion |
| A venue reports a trading halt for a defined instrument and period | The reported market status, scope, occurrence or effective meaning, origin, and qualifications | Status evidence grants no order or execution authority |
| A statistical authority publishes a preliminary value for a declared reference period | The value, unit, period, preliminary status, publication time, and origin | Preliminary qualification and period meaning remain explicit |
| A publisher issues a correction to an earlier report | The new publication fact, correction status, issue time, origin, and source-established lineage | The correction is a new event and the earlier report remains immutable |
| An external measurement source reports an approximate traffic range for a stated interval | The range, approximation, measurement dimension, interval, subject scope, and origin | Uncertainty and temporal scope remain source-reported evidence |

### 17.2 Invalid payload treatment

| Candidate treatment | Why invalid | Required resolution |
| --- | --- | --- |
| Preserve only a numeric value and omit its unit or basis | The number lacks Semantic Sufficiency | Preserve the source-established meaning or do not admit the candidate |
| Fill missing currency from Registry | It manufactures Observation evidence and crosses ownership | Leave currency absent or qualified under the applicable frozen contract |
| Use receipt time as observation time | It changes temporal meaning | Keep operational and observation times distinct |
| Store a provider status code as canonical meaning | Provider-private packaging leaks into payload | Express established meaning in governed vocabulary or do not admit it |
| Average two disagreeing source values | It creates a platform calculation | Preserve separate attributed events |
| Copy an analyst recommendation into Observation Payload | Recommendation is excluded judgment | Preserve only an eligible publication fact, if independently admitted |
| Add an internal confidence score beside a source estimate as though both came from the source | It confuses assessment with testimony | Keep Trust or analytical output separately owned |
| Replace an original value when a revision arrives | It mutates earlier Payload Meaning | Preserve a new revision event and source-established lineage |
| Include earnings results and a dividend declaration in one multi-class payload | It violates one-fact and one-class granularity | Represent independently qualifying events separately |
| Treat a provider-returned symbol as canonical subject identity | Provider evidence cannot adjudicate identity | Use only an already-governed identity reference or preserve an explicitly external subject claim |

### 17.3 Temporal examples

**Publication and reference period.** A macroeconomic value may refer to one calendar period and be published later. Both meanings are material and neither replaces the other.

**Announcement and effectiveness.** A split announced today for a later effective date preserves publication and declared-effective meanings. It does not assert that the split became effective.

**Observation and receipt.** A market value observed by the source before the platform receives it retains the source observation time. Receipt time remains separate provenance or operational context.

**Date-only evidence.** A source-declared payment date with no instant or time zone remains a date-level claim. Canonicalization does not invent a timestamp.

### 17.4 Uncertainty examples

**Preliminary publication.** A preliminary measurement remains preliminary even when it is structurally complete and clearly attributed.

**Source range.** A reported interval remains an interval. Observation does not select its midpoint.

**Unknown value.** A source marking a term unknown is different from the source omitting the term and from declaring the term not applicable.

**Conflicting sources.** Two origins reporting different values produce separately attributable claims. Payload does not choose, merge, or average them.

### 17.5 Correction and revision examples

**Corrected price publication.** The correction is a new Market Price event when that is the fact kind corrected. The earlier event retains its original payload and class.

**Revised macroeconomic series.** A revised measurement is a new Macroeconomic Publication event with its own value, period, publication time, revision status, origin, and source-established lineage.

**Retracted news report.** The retraction is a new News Publication event preserving that the publisher withdrew the prior report. Observation does not infer what is true instead.

**Later measurement.** A later market value is not a correction merely because it differs from an earlier value. It is a later measurement unless the source establishes correction or revision lineage.

## 18. Independent Review and Conformance

A future specification, implementation proposal, or payload-extension proposal conforms to M39-WP4 only when objective review establishes every requirement below.

| Identifier | Required proof |
| --- | --- |
| SEM-01 | Each payload preserves one Classifying Fact and satisfies Semantic Sufficiency without copying provider packaging |
| SEM-02 | Material values, terms, units, bases, scopes, statuses, and qualifications retain their source-established meaning |
| SEM-03 | Missing, unknown, unavailable, withheld, not-applicable, and qualified meanings are not fabricated or silently collapsed |
| SEM-04 | Equivalent claims retain equivalent Payload Meaning across qualifying sources and relays |
| CLS-01 | Every payload remains within exactly one M39-WP3 class and no payload bypasses mixed-content separation |
| SRC-01 | Source eligibility, Observation Origin, and Payload Meaning remain independent |
| SRC-02 | The payload remains an attributable source claim and does not become truth, quality, identity, judgment, or authority |
| TMP-01 | Every material source-established temporal claim has explicit meaning |
| TMP-02 | Observation, occurrence, publication, effective, reference-period, receipt, retrieval, and cache meanings are not improperly substituted or collapsed |
| TMP-03 | Temporal precision, interval, and qualification remain faithful to source meaning |
| PRV-01 | Observation Origin and materially relevant relay roles remain distinguishable |
| PRV-02 | Provider identity and provenance do not determine Payload Meaning, classification, identity, quality, freshness, or authority |
| UNC-01 | Material source-reported uncertainty, absence, dispute, and limitation remain explicit |
| UNC-02 | Platform assessment remains separate from source-reported uncertainty |
| COR-01 | Corrections, revisions, retractions, and later measurements are new events and do not mutate earlier meaning |
| COR-02 | Correction Lineage reflects source-established relationships and differing values alone do not create lineage |
| OWN-01 | Market Intelligence remains the sole semantic owner of Observation Payload |
| OWN-02 | Every adjacent constitutional and non-domain authority boundary retains its prior ownership |
| NEU-01 | No provider, SDK, field, endpoint, protocol, serialization, transport, storage, runtime, API, or implementation concept defines payload semantics |
| SEP-01 | No payload calculation, analytics, prediction, recommendation, strategy, portfolio meaning, execution, transaction, or action authority is introduced |
| EXT-01 | A proposed extension is provider-neutral, semantically distinct, and additive |
| EXT-02 | An extension changes no existing Payload Meaning, class boundary, frozen contract, or consumer obligation |
| CMP-01 | M38 contracts remain unchanged |
| CMP-02 | M39-WP1 concrete contract, public boundary, availability, derivation, normalization, feature, rollback, and execution-separation rules remain unchanged |
| CMP-03 | M39-WP2 definitions, eligibility, exclusions, ownership, provenance, reproducibility, and extension rules remain unchanged |
| CMP-04 | M39-WP3 class names, boundaries, one-class rule, correction classification, and extension rules remain unchanged |
| SCP-01 | The proposal grants no implementation, provider, runtime, transport, storage, serialization, API, or public-exposure authority |

The independent reviewer SHALL verify:

- constitutional consistency;
- complete compatibility with M38 and M39-WP1 through M39-WP3;
- deterministic and provider-neutral terminology;
- one-fact and one-class payload scope;
- semantic sufficiency without fabrication;
- complete temporal preservation;
- complete provenance preservation;
- explicit uncertainty and absence semantics;
- immutable correction and revision treatment;
- deterministic ownership;
- additive future extensibility;
- absence of provider, runtime, transport, storage, serialization, API, and implementation assumptions; and
- absence of implicit implementation authorization.

Conformance establishes constitutional payload validity only. It does not approve a provider, implementation, runtime, storage model, transport, serialization, schema, API, migration, feature activation, or public contract.

## 19. Canonical Closure

M39-WP4 defines the constitutional semantic payload boundary for future Market Observation work.

After ratification:

- every admitted Observation Payload MUST preserve one provider-neutral Classifying Fact with Semantic Sufficiency;
- payload, source, origin, classification, and adjacent-domain authority MUST remain distinct;
- temporal meaning, provenance, uncertainty, absence, and correction lineage MUST remain faithful to source meaning;
- provider and mechanism changes MUST remain invisible to existing Payload Meaning;
- future payload semantics MUST be additive;
- M38 and M39-WP1 through M39-WP3 MUST remain authoritative and unchanged; and
- this specification MUST NOT be treated as implementation or public-exposure authority.

Nothing in this specification reopens a completed milestone or authorizes implementation.
