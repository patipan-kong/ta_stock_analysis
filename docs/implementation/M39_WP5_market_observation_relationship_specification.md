# M39-WP5 — Market Observation Relationship Specification

**Status:** Canonical specification candidate for independent constitutional review

**Authority:** M39-WP5

**Nature:** Normative constitutional relationship specification

## 1. Purpose

This specification defines the canonical semantic boundary for relationships among Market Observation Events.

An Observation Relationship preserves a provider-neutral association that is necessary to describe how two or more otherwise immutable Observation Events relate in source-established meaning. It does not merge those events, change their meanings, or create authority over any adjacent domain.

Relationship answers:

> What semantic association, if any, is explicitly established among otherwise distinct Observation Events?

Relationship does not answer:

- who or what qualifies as an Observation Source;
- what any Observation Event means by itself;
- what Canonical Observation Class applies;
- how an Observation Event or relationship is identified, represented, stored, traversed, exposed, or processed;
- which event is true, trusted, important, current, preferred, actionable, or legally effective;
- whether one observed fact caused another; or
- what conclusion or action belongs to any consumer.

This specification establishes semantic obligations only. It does not authorize implementation, provider integration, runtime adoption, persistence, transport, public exposure, or amendment of an existing contract.

## 2. Authority and Compatibility

This specification is subordinate to the Platform Architecture and preserves all ratified governance through M39-WP4.

In particular:

- M38 remains complete and frozen;
- the M38 reserved market contribution and all M38 envelope, attachment, composition, availability, and ownership contracts remain unchanged;
- M39-WP1 remains complete and frozen;
- the M39-WP1 `MarketObservation` contract, public boundary, availability model, exact provider derivation, canonical normalization reuse, feature expectations, and execution separation remain unchanged;
- M39-WP2 remains authoritative for Observation Source eligibility and the meanings of Observation Event, Observation Payload, Observation Timestamp, and Observation Origin;
- M39-WP3 remains authoritative for Canonical Observation Classes, the Classifying Fact, the exactly-one-class rule, mixed-content treatment, and additive class admission;
- M39-WP4 remains authoritative for provider-neutral Payload Meaning, Semantic Sufficiency, temporal and provenance preservation, uncertainty, absence, Correction Lineage, and immutable correction treatment;
- Market Intelligence remains the sole semantic owner of Market Observation and Observation Relationships;
- Asset Foundation remains the sole owner of canonical asset identity and Registry adjudication;
- Connectivity & Ingestion retains ownership of external-fact ingestion toward ledger truth;
- all existing ledger, portfolio, decision, authorization, execution, provider, runtime, storage, analytics, Trust, and Experience boundaries remain unchanged; and
- Observation remains evidence, never identity authority, ledger truth, investment judgment, execution authority, or presentation authority.

This specification elaborates semantic association among the immutable Observation Events established by M39-WP2. It SHALL NOT redefine Observation Source, Observation Event, Observation Payload, Observation Timestamp, Observation Origin, Observation Classification, Payload Meaning, Correction Lineage, or Observation identity.

No general concept in this specification overrides a more specific frozen contract.

## 3. Scope

M39-WP5 defines:

- provider-neutral relationship principles;
- canonical semantic relationship vocabulary;
- semantic independence and dependency;
- related-observation semantics;
- conceptual parent and child semantics;
- correction, revision, retraction, and supersession relationships;
- semantic grouping and cross-reference semantics;
- causal independence;
- relationship ownership and adjacent-domain boundaries;
- compatibility with M38 and M39-WP1 through M39-WP4;
- additive relationship extensibility;
- constitutional invariants;
- prohibited interpretations;
- informative examples; and
- objective independent-review criteria.

This specification defines semantic relationships only.

### 3.1 Out of scope

The following are outside M39-WP5:

- graph implementation;
- graph topology or traversal;
- database links or foreign keys;
- object references or pointers;
- runtime graphs;
- event sourcing;
- directed acyclic graph implementation;
- queues, scheduling, orchestration, or workflow;
- APIs, endpoints, requests, or responses;
- storage, persistence, retention, replay, or deletion;
- serialization, schemas, fields, enums, tokens, or identifiers;
- transport or protocols;
- provider mappings, adapters, SDK behavior, or provider routing;
- caching or materialized projections;
- relationship discovery algorithms;
- inferred similarity, correlation, causation, or importance;
- ranking, selection, conflict resolution, reconciliation, or truth adjudication;
- alerts, screeners, watchlists, calculations, analytics, predictions, recommendations, or strategies;
- orders, execution, transactions, or portfolio behavior;
- authentication, authorization, approval, or human authority;
- observation identity allocation or resolution;
- lifecycle policy for non-observation domain objects; and
- implementation or public exposure of any relationship.

Naming an excluded mechanism to prohibit it does not authorize or design that mechanism.

## 4. Canonical Vocabulary

The terms in this section are normative.

### 4.1 Observation Relationship

An **Observation Relationship** is a provider-neutral semantic assertion that associates two or more distinct Observation Events without changing the identity, class, payload, provenance, temporal meaning, or immutability of any associated event.

An Observation Relationship:

- MUST have one canonical Relationship Kind;
- MUST be supported by source-established meaning preserved in attributable event context;
- MUST preserve every participating event as a distinct Observation Event;
- MUST state direction only when direction is part of the relationship meaning;
- MUST preserve the semantic scope to which the association applies;
- MUST NOT manufacture evidence absent from the events or their attributable source context; and
- MUST NOT become identity, truth, quality, causality, ordering, selection, action, or implementation authority.

An Observation Relationship is not an Observation Event and does not create an additional Classifying Fact.

### 4.2 Relationship Assertion

A **Relationship Assertion** is one application of exactly one Relationship Kind to a defined set of participating Observation Events.

One pair of events MAY carry more than one Relationship Assertion only when each assertion:

- expresses a distinct canonical meaning;
- is independently supported;
- does not contradict another assertion; and
- remains separately interpretable.

Multiple meanings MUST NOT be collapsed into one ambiguous assertion.

### 4.3 Relationship Kind

A **Relationship Kind** is a canonical, provider-neutral semantic category defined by this specification or admitted through the additive extension rules in §13.

Relationship Kind is distinct from:

- Observation Classification;
- provider terminology;
- source category;
- asset relationship;
- object lifecycle;
- graph edge type;
- storage relation; and
- consumer interpretation.

A Relationship Kind classifies the association, not any participating Observation Event.

### 4.4 Relationship Meaning

**Relationship Meaning** is the complete provider-neutral semantic content of a Relationship Assertion: its Relationship Kind, direction where applicable, endpoint roles, semantic scope, source-established qualification, and attributable basis.

Relationship Meaning MUST NOT include implementation representation, provider-private terminology, inferred consequence, or consumer policy.

### 4.5 Relationship Endpoint

A **Relationship Endpoint** is the conceptual role occupied by one participating Observation Event within a Relationship Assertion.

An endpoint denotes an already-distinct Observation Event. It does not define:

- an observation identifier;
- identifier syntax or allocation;
- object reference;
- lookup or resolution behavior;
- storage address;
- public resource; or
- ownership of the event.

This specification presupposes only that participating events are semantically distinguishable under applicable governance. It does not establish how they are referenced.

### 4.6 Semantic Independence

**Semantic Independence** is the condition in which an Observation Event retains its complete Payload Meaning, classification, attribution, and temporal meaning without another Observation Event being necessary to understand the source-established claim.

Semantic Independence is the default.

The existence of shared subject matter, chronology, source, class, value, artifact, or provenance MUST NOT by itself negate Semantic Independence.

### 4.7 Semantic Dependency

A **Semantic Dependency** is a directed relationship in which the source-established meaning of a dependent Observation Event expressly relies on another Observation Event for material context.

Semantic Dependency:

- MUST identify the dependent and supporting endpoint roles conceptually;
- MUST be explicit in the attributable source meaning;
- MUST be limited to the material semantic scope of that reliance;
- MUST NOT permit an opaque or semantically insufficient payload;
- MUST NOT transfer payload, classification, ownership, truth, or authority from the supporting event; and
- MUST NOT mean that the dependent event ceases to exist if the supporting event is unavailable, disputed, retracted, or superseded.

Every dependent event remains an immutable Observation Event with its own Claim Content, class, temporal meaning, provenance, and uncertainty under M39-WP2 through M39-WP4.

### 4.8 Related Observation

A **Related Observation** relationship is a symmetric semantic association between distinct Observation Events that share explicit, material, source-established context but do not require direction, dependency, containment, correction, revision, retraction, supersession, or causation.

Related Observation is the weakest canonical association.

It MUST NOT be used as a catch-all for similarity, proximity, shared provider, shared asset, shared class, or consumer convenience.

### 4.9 Parent/Child Relationship

A **Parent/Child Relationship** is a directed, conceptual containment relationship in which a source-established composite observation context contains or introduces one or more separately qualifying Observation Events.

The parent is the containing or introducing observation context. A child is a separately immutable event whose fact meaning is associated with that context.

Parent/Child:

- MUST preserve the source-established containment meaning;
- MUST NOT make the parent the owner of the child;
- MUST NOT merge the parent and child payloads;
- MUST NOT change the class of either event;
- MUST NOT imply identity inheritance, asset hierarchy, temporal precedence, causal dependence, lifecycle control, or deletion cascade; and
- MUST NOT be inferred merely because events arrived together or were stored together.

The terms parent and child are semantic roles only. They do not define objects, references, records, trees, graphs, or runtime structure.

### 4.10 Correction Relationship

A **Correction Relationship** is a directed relationship from a new correction event to an earlier event when the Observation Origin explicitly establishes that the earlier claim was erroneous or materially inaccurate and the new event corrects it within a stated scope.

A Correction Relationship:

- MUST preserve both events and both Payload Meanings;
- MUST preserve the source-established correction scope;
- MUST NOT mutate, erase, or retroactively rewrite the earlier event;
- MUST NOT imply that every part of the earlier event was incorrect unless the source establishes that scope;
- MUST NOT be inferred from differing values alone; and
- MUST NOT establish platform truth or downstream consequence.

### 4.11 Revision Relationship

A **Revision Relationship** is a directed relationship from a new revision event to an earlier event when the Observation Origin explicitly publishes an updated measurement, term, estimate, status, or statement for the same source-established semantic scope.

A Revision Relationship:

- MUST preserve the distinction between revision and correction when the source does so;
- MUST preserve both events and their temporal meanings;
- MUST NOT imply error unless the source characterizes the earlier claim as erroneous;
- MUST NOT collapse a time series or later independent measurement into revision lineage; and
- MUST NOT establish consumer preference among versions.

### 4.12 Retraction Relationship

A **Retraction Relationship** is a directed relationship from a new retraction event to an earlier event when the Observation Origin explicitly withdraws, disavows, or revokes the earlier claim.

A Retraction Relationship:

- MUST preserve the earlier event as historical observation evidence;
- MUST preserve the source-established scope of withdrawal;
- MAY exist without a replacement claim;
- MUST NOT infer replacement truth;
- MUST NOT erase the earlier event; and
- MUST NOT determine legal, accounting, portfolio, analytical, or action consequences.

### 4.13 Supersession Relationship

A **Supersession Relationship** is a directed relationship from a later event to an earlier event when the Observation Origin explicitly declares that the later claim replaces the earlier claim for a stated semantic scope.

Supersession:

- MUST be source-established;
- MUST preserve both events as immutable evidence;
- MUST preserve the exact scope and qualification of the replacement declaration;
- MUST NOT be inferred from recency, higher version notation, differing value, apparent completeness, or consumer preference;
- MUST NOT mean deletion, invalidity, truth, trust, legal effect, or universal preference;
- MUST NOT authorize a current, latest, effective, or preferred projection; and
- MUST NOT change either event’s class or Payload Meaning.

Correction, Revision, Retraction, and Supersession are distinct Relationship Kinds. A source MAY establish more than one between the same events, but each MUST remain a separate Relationship Assertion under §4.2.

### 4.14 Cross-Reference Relationship

A **Cross-Reference Relationship** is a directed relationship in which one Observation Event explicitly cites, mentions, incorporates by reference, or points to another Observation Event as source-established context.

A Cross-Reference Relationship:

- MUST preserve the nature and direction of the reference;
- MUST NOT by itself imply Semantic Dependency;
- MUST NOT by itself imply endorsement, agreement, correction, revision, retraction, supersession, containment, or causation;
- MUST NOT substitute for Semantic Sufficiency under M39-WP4; and
- MUST NOT import the referenced payload into the referencing event.

### 4.15 Semantic Observation Group

A **Semantic Observation Group** is a conceptual association of distinct Observation Events that share one explicit, provider-neutral, source-established grouping context.

A Semantic Observation Group:

- MUST have a determinate semantic basis;
- MUST preserve each member as an independent Observation Event;
- MUST NOT itself become an Observation Event, Observation Payload, Observation Class, asset, portfolio, collection product, or authority object;
- MUST NOT imply order, dependency, hierarchy, correction, supersession, causation, completeness, or preferred membership;
- MUST NOT admit events solely for consumer convenience, co-location, arrival batch, or provider packaging; and
- MUST NOT create new Claim Content.

Group membership is a semantic association only. This specification does not define a group identifier, container, record, lifecycle, query, or representation.

### 4.16 Causal Independence

**Causal Independence** is the constitutional rule that an Observation Relationship does not establish that one observed fact caused, influenced, predicted, explains, or is responsible for another.

Chronology, correlation, shared subject, shared origin, cross-reference, dependency, containment, correction, revision, retraction, supersession, or grouping MUST NOT be interpreted as causation.

An attributable publication MAY itself report a causal claim when that claim is otherwise admissible under M39-WP2 through M39-WP4. Preserving the reported claim does not make causation a canonical Observation Relationship or a platform conclusion.

## 5. Relationship Principles

### 5.1 Semantic-first

Relationship meaning MUST be determined from the provider-neutral semantics of the participating events and their attributable source context.

Provider labels, fields, products, identifiers, routes, or packaging MUST NOT determine Relationship Kind.

### 5.2 Distinct-event preservation

Every participating Observation Event MUST remain distinct, immutable, and independently governed.

A relationship MUST NOT:

- combine events into one event;
- split an event;
- copy or move Claim Content;
- change an event’s Observation Origin, Timestamp, Classification, Semantic Subject, uncertainty, or provenance; or
- rewrite an event’s Payload Meaning.

### 5.3 Explicit evidence

A relationship MUST NOT be asserted merely because it appears likely, useful, conventional, sequential, correlated, or analytically plausible.

Correction, Revision, Retraction, Supersession, Semantic Dependency, Parent/Child, Cross-Reference, and grouping context MUST be supported by attributable source meaning.

Related Observation MUST be supported by explicit material context and MUST NOT be a fallback for unresolved meaning.

When support is insufficient or ambiguous, no canonical relationship exists.

### 5.4 Determinism

Equivalent event meanings and equivalent source-established context under the same governed vocabulary MUST yield the same relationship disposition.

Relationship determination MUST NOT depend on provider identity, runtime path, storage location, processing order, consumer, portfolio, user, workspace, or mutable platform state.

### 5.5 Minimum assertion

Only the narrowest relationship meaning established by the evidence MAY be asserted.

A weaker relationship MUST NOT be inflated into dependency, containment, correction, revision, retraction, or supersession. A stronger relationship MUST NOT be diluted when doing so would lose material source meaning.

### 5.6 Direction fidelity

Direction MUST be preserved for directed Relationship Kinds and MUST NOT be manufactured for symmetric Relationship Kinds.

Reversing a directed relationship changes its meaning and SHALL NOT be treated as equivalent.

### 5.7 Independence by default

Distinct Observation Events MUST be treated as semantically independent unless a canonical relationship is explicitly established.

The absence of a relationship:

- MUST NOT be interpreted as evidence of unrelated real-world facts;
- MUST NOT imply disagreement or agreement;
- MUST NOT imply provider or observation failure; and
- MUST NOT authorize inferred linkage.

### 5.8 Provider and mechanism neutrality

Relationship semantics MUST remain independent of provider, runtime, transport, storage, serialization, API, graph, database, object model, and implementation.

Adding, replacing, or removing a provider or mechanism MUST NOT alter an existing canonical relationship meaning.

### 5.9 Evidence, never authority

A relationship describes source-established association among observations. It does not validate the events, reconcile conflicts, select truth, establish canonical identity, authorize action, or transfer ownership.

### 5.10 Single responsibility

Relationship vocabulary MUST describe semantic association only.

It MUST NOT absorb classification, payload, provenance, identity, analytics, causality, workflow, lifecycle control, or consumer policy.

## 6. Canonical Relationship Types

The canonical Relationship Kinds established by M39-WP5 are:

| Relationship Kind | Direction | Canonical meaning | Explicitly does not mean |
| --- | --- | --- | --- |
| Related Observation | Symmetric | Distinct events share explicit, material, source-established context | Similarity, dependency, containment, lifecycle, causation, or catch-all linkage |
| Semantic Dependency | Directed | One event expressly relies on another for material source-established context | Shared payload, validity dependence, authority transfer, or lifecycle control |
| Parent/Child | Directed | A source-established composite observation context contains or introduces a separately qualifying event | Object hierarchy, identity inheritance, cascade, ownership, or causation |
| Correction | Directed | A new event explicitly corrects an earlier erroneous or materially inaccurate claim within stated scope | Mutation, deletion, truth adjudication, or inferred replacement |
| Revision | Directed | A new event explicitly updates an earlier measurement, term, estimate, status, or statement within stated scope | Necessarily an error, an independent later measurement, or consumer preference |
| Retraction | Directed | A new event explicitly withdraws, disavows, or revokes an earlier claim | Erasure, replacement truth, or downstream consequence |
| Supersession | Directed | A new event is explicitly declared to replace an earlier claim within stated scope | Deletion, universal invalidity, latest-selection policy, or truth |
| Cross-Reference | Directed | One event explicitly cites, mentions, or points to another as context | Dependency, endorsement, correction, containment, or causation |
| Semantic Group Membership | Non-directional membership | Events share one explicit source-established grouping context | New fact, order, hierarchy, completeness, workflow, or container implementation |

No `OTHER`, `UNKNOWN`, generic `LINK`, provider-private, opaque, or implementation-default Relationship Kind is established.

Semantic Independence and Causal Independence are constitutional conditions, not Relationship Kinds.

## 7. Relationship Semantics

### 7.1 Qualification before relationship

Every proposed endpoint MUST already qualify as a distinct Observation Event under M39-WP2 and MUST satisfy the applicable M39-WP3 and M39-WP4 contracts.

Relationship SHALL NOT:

- make an ineligible claim eligible;
- cure zero or multiple classification outcomes;
- make a semantically insufficient payload sufficient;
- create an Observation Origin or Timestamp;
- assign canonical subject identity; or
- authorize public exposure.

### 7.2 Exactly one disposition per proposed assertion

For each proposed Relationship Assertion, constitutional review has exactly three dispositions:

1. **One matching kind:** the assertion MAY be admitted, subject to all other governance.
2. **Zero matching kinds:** the assertion MUST NOT be admitted under this specification. Either the events remain semantically independent or separately governed additive authority is required.
3. **Multiple apparent matching kinds:** the assertion is ambiguous and MUST NOT be admitted in that form. The source-established meaning and semantic scope MUST be refined into one kind or, when independently supported, into distinct assertions under §4.2.

These are specification dispositions, not runtime statuses, API values, errors, storage states, or workflow outcomes.

### 7.3 Endpoint integrity

Each relationship endpoint MUST denote exactly one already-distinct Observation Event in the applicable semantic context.

An endpoint MUST NOT be:

- an asset, provider, source category, artifact, portfolio, order, transaction, user, workspace, runtime component, or storage object;
- an unresolved set of possible events;
- a mutable “latest” or “current” event selection;
- a provider identifier used as observation identity; or
- an execution evidence reference represented as Market Observation identity.

This section defines semantic integrity only and does not establish an endpoint representation.

### 7.4 Scope fidelity

A relationship MUST apply only to the source-established scope of association.

Partial correction, revision, retraction, or supersession MUST NOT be widened to an entire event, artifact, subject, series, or history unless the source explicitly establishes that wider scope.

Unrelated portions of participating events retain their original meaning.

### 7.5 Relationship and payload separation

Relationship meaning MUST remain distinct from the Payload Meaning of every endpoint.

A relationship:

- MAY preserve an association necessary to understand source-established context;
- MUST NOT copy, synthesize, or replace Claim Content;
- MUST NOT serve as an opaque substitute for material payload semantics;
- MUST NOT change uncertainty, absence, qualification, or temporal precision; and
- MUST NOT cause one endpoint’s payload to be interpreted as part of another endpoint’s payload.

### 7.6 Relationship and classification separation

Every endpoint retains exactly one Canonical Observation Class under M39-WP3.

Relationship Kind:

- MUST NOT become an Observation Class;
- MUST NOT select or change an endpoint’s class;
- MUST NOT create a correction, revision, retraction, supersession, dependency, or grouping class; and
- MUST NOT permit one event to acquire multiple classes.

Endpoints in one relationship MAY have the same or different classes when their independently governed meanings require it.

### 7.7 Relationship and source separation

Observation Source answers:

> Who can witness or relay the fact?

Observation Origin answers:

> Who or what is responsible for the claim?

Observation Classification answers:

> What kind of fact is represented?

Observation Payload answers:

> What provider-neutral fact content is preserved?

Observation Relationship answers:

> What source-established semantic association exists among distinct events?

These questions MUST remain independent. An answer to one MUST NOT determine another by implication.

### 7.8 Temporal separation

Relationship direction MUST NOT be inferred from event timestamps alone.

Earlier and later times MAY support interpretation only when the attributable source meaning independently establishes the Relationship Kind and direction.

A relationship MUST NOT:

- replace any endpoint’s Observation Timestamp;
- collapse publication, occurrence, observation, effective, or reference-period meanings;
- infer correction, revision, retraction, or supersession from chronology;
- convert receipt, retrieval, cache, storage, schedule, or display order into semantic order; or
- establish freshness or currentness.

### 7.9 Provenance and uncertainty

The attributable basis of a relationship MUST be preserved without becoming provider-dependent semantics.

Relationship uncertainty or qualification explicitly stated by the source MUST remain explicit. Platform uncertainty about whether a relationship exists MUST NOT be converted into a canonical relationship.

Provider confidence, source quality, platform trust, and validation results MAY be assessed under existing governance but MUST NOT redefine Relationship Kind or endpoint meaning.

### 7.10 Disagreement and conflict

Conflicting, inconsistent, or differing events do not acquire a canonical relationship merely because they concern similar subject matter.

Relationship MUST NOT:

- reconcile competing claims;
- declare one endpoint correct;
- rank evidence;
- select preferred evidence;
- merge disagreement into one value; or
- infer correction, revision, retraction, or supersession.

Trust, validation, reconciliation, analytics, and consumer selection remain with their existing constitutional owners.

## 8. Relationship Boundaries and Boundary Matrix

| Boundary question | Inside Observation Relationship | Outside Observation Relationship | Required resolution |
| --- | --- | --- | --- |
| Are two events associated? | One explicit provider-neutral semantic association supported by attributable meaning | Similarity, co-arrival, shared storage, consumer convenience, or speculation | Admit only the narrow supported Relationship Kind; otherwise preserve independence |
| Does one event need another for context? | Explicit material Semantic Dependency | Opaque payload, shared ownership, validity dependence, or lifecycle control | Preserve each event’s Semantic Sufficiency and distinct meaning |
| Is one event contained by another context? | Source-established Parent/Child containment | Object hierarchy, identity inheritance, cascade, or graph topology | Preserve conceptual containment only |
| Did a source correct an earlier claim? | Explicit scoped Correction Relationship | Value comparison, platform verdict, overwrite, or deletion | Preserve both events and source-established correction scope |
| Did a source revise an earlier claim? | Explicit scoped Revision Relationship | Independent later measurement or inferred version preference | Preserve both events and the revision meaning |
| Did a source withdraw an earlier claim? | Explicit Retraction Relationship | Historical erasure or inferred replacement truth | Preserve the retraction and the earlier evidence |
| Did a source replace an earlier claim? | Explicit scoped Supersession Relationship | “Latest” selection, universal invalidity, deletion, or truth | Preserve the declaration without selecting for consumers |
| Does one event cite another? | Directed Cross-Reference | Automatic dependency, endorsement, or payload import | Preserve citation semantics only |
| Do events share one semantic context? | Explicit Semantic Observation Group membership | Batch, provider response, folder, cache, screen, or arbitrary collection | Preserve only source-established grouping context |
| Did one fact cause another? | No causal conclusion | Correlation, explanation, influence, prediction, or causal inference | Keep relationships causally independent |
| Which event is current or preferred? | Nothing | Projection, ranking, conflict resolution, or consumer policy | Existing consumer or evaluation owner decides without rewriting relationships |
| What is the relationship identifier? | No identity decision | Identifier, key, reference syntax, URI, or lookup behavior | Govern separately without changing relationship meaning |
| How is the relationship represented? | No representation choice | Field, schema, enum, object, edge, table, serialization, or API | Govern separately without changing semantics |
| How is the relationship retained or traversed? | No persistence or traversal behavior | Graph, database, index, cache, event store, query, or replay | Operational owners retain responsibility |

## 9. Ownership Model

Every concept has exactly one semantic owner. Reference, attribution, custody, consumption, grouping, rendering, or assessment does not create shared ownership.

| Concept or boundary | Canonical owner | Relationship boundary |
| --- | --- | --- |
| Observation Relationship vocabulary and semantics | Market Intelligence | Sole semantic ownership under this specification |
| Observation Source, Event, Timestamp, and Origin semantics | Market Intelligence under M39-WP2 | Remain unchanged and constrain endpoint eligibility and attribution |
| Observation Classification | Market Intelligence under M39-WP3 | Remains attached to each endpoint and is not determined by Relationship Kind |
| Observation Payload and Correction Lineage | Market Intelligence under M39-WP4 | Endpoint meanings remain immutable; relationship preserves association without importing or changing payload |
| External claim and source-association authorship | Observation Origin under M39-WP2 | Origin supplies attributable claims and association meaning but does not own platform relationship vocabulary or downstream verdicts |
| Canonical asset identity, Registry classification, and asset relationships | Asset Foundation | Observation relationships cannot create, infer, merge, supersede, or adjudicate asset identity or asset relationships |
| External-fact ingestion toward ledger truth | Connectivity & Ingestion | Observation relationships do not create ingestion proposals, reconciliation outcomes, or truth-path authority |
| Transactions and financial truth | Ledger & Accounting | Observation relationships cannot create, amend, link, validate, supersede, or reverse ledger facts |
| Portfolio relationships and derivations | Portfolio Intelligence | Portfolio membership, exposure, valuation, performance, and risk remain outside Observation |
| Analytics and derived relationships | The constitutional owner of each derived result | Similarity, correlation, causality, clustering, scoring, and inference do not become Observation Relationships |
| Investment conclusions and actions | Decision Intelligence and existing frozen action boundaries | Relationship does not create prediction, recommendation, strategy, intent, approval, or execution |
| Trust, quality, and conflict assessment | Trust & Evaluation or another frozen assessment owner | Assessment MAY consume relationships but MUST NOT mutate endpoint or relationship meaning |
| Authentication, authorization, approval, and human authority | Existing non-domain authority boundaries | Relationship supplies no identity proof, permission, delegation, approval, or authority |
| Provider-specific interaction and translation | Existing Provider Layer | Provider terminology MAY be translated but MUST NOT own or alter canonical relationship semantics |
| Runtime and orchestration | Existing runtime and operational owners | May coordinate future capabilities only under separate authority and never owns relationship meaning |
| Storage and transport | Existing persistence and infrastructure owners | May preserve future representations only under separate authority and never becomes semantic owner |
| Experience composition | Experience Platform | May render future relationship meaning under separate authority but cannot reinterpret or derive it |
| Future AI modules | Existing owner according to output meaning | May consume observations but inferred associations, explanations, and conclusions remain outside canonical Observation Relationship |

No row grants new authority. Prior ownership remains authoritative.

## 10. Correction, Revision, Retraction, and Supersession Integrity

### 10.1 New-event rule

A correction, revision, retraction, or superseding claim MUST be a new Observation Event under M39-WP2.

The new event:

- MUST preserve its own Claim Content;
- MUST retain its own classification, temporal meaning, provenance, uncertainty, and qualification;
- MUST preserve the lifecycle assertion made by the source;
- MAY participate in the corresponding Relationship Assertion only when the source establishes it; and
- MUST NOT mutate the earlier event or its Payload Meaning.

### 10.2 Lineage fidelity

The relationship vocabulary in this specification elaborates, but does not redefine, Correction Lineage under M39-WP4.

Correction Lineage MUST distinguish, where source-established:

- correction of an erroneous or materially inaccurate prior claim;
- revision of a previously published measurement, term, estimate, status, or statement;
- retraction or withdrawal of a prior claim;
- supersession declared by the origin; and
- a later independent measurement with no lifecycle relationship.

A later event MUST NOT be labeled correction, revision, retraction, or supersession solely because it differs from or follows an earlier event.

### 10.3 No silent replacement

Relationship semantics MUST NOT authorize:

- overwriting or deleting an earlier event;
- presenting the later event as though it were the only historical claim;
- erasing earlier uncertainty or qualification;
- merging lifecycle events into one mutable payload;
- inferring lineage absent source support; or
- treating “latest,” “current,” “preferred,” or “effective” selection as intrinsic relationship meaning unless the source claim itself establishes only that factual declaration.

Even when a source declares an event current, preferred, or effective, consumer selection remains outside this boundary.

### 10.4 No transitive inflation

Correction, Revision, Retraction, and Supersession MUST NOT be assumed transitive.

If event C relates to event B and event B relates to event A, no relationship from C to A exists unless independently source-established.

Relationship chains MUST NOT widen scope, erase intermediate events, or create an inferred canonical version.

### 10.5 Classification stability

Lifecycle relationship alone SHALL NOT create a separate Observation Class.

Each new event MUST be classified according to the kind of fact it corrects, revises, retracts, supersedes, or newly reports under M39-WP3. The earlier event’s class and meaning MUST NOT change.

## 11. Grouping and Cross-Reference Integrity

### 11.1 Semantic grouping

Grouping MAY preserve an explicit common publication, release, episode, series, reference period, or other provider-neutral context only when that context is source-established and material.

Grouping MUST NOT:

- make the group a new external fact;
- imply that membership is complete;
- infer a sequence or hierarchy;
- merge member payloads;
- create a composite class;
- create portfolio, watchlist, screener, alert, or user collection semantics;
- depend on provider packaging or delivery batch; or
- become a substitute for a more specific relationship.

### 11.2 Parent and child containment

Parent/Child MUST be used only when a source-established containing observation context and separately qualifying contained event both exist.

An artifact that merely carries multiple facts is not automatically an Observation Event and therefore is not automatically a parent.

When the containing context is not itself a qualifying Observation Event, Parent/Child MUST NOT be asserted. Eligible facts MAY still retain common grouping or provenance where prior governance permits.

### 11.3 Cross-reference fidelity

Cross-Reference MUST preserve what the source referenced and the direction of reference without importing the referenced claim.

A citation to:

- an earlier publication does not automatically create dependency;
- a source document does not automatically endorse every statement in it;
- a prior value does not automatically correct or revise it;
- a future event does not prove that event occurred; and
- another subject does not establish an Asset Foundation relationship.

### 11.4 No inferred closure

Related Observation, Parent/Child, Cross-Reference, and Semantic Group Membership MUST NOT be assumed transitive.

Shared association with one event or group MUST NOT create an association between all other participants.

No relationship set MAY be treated as complete unless that completeness is itself explicitly established by admissible source meaning, and even such a claim does not authorize implementation-level closure.

## 12. Compatibility Requirements

### 12.1 Frozen compatibility

M39-WP5 MUST remain compatible with:

- M38 projection and contribution governance;
- M39-WP1 public resource, concrete `MarketObservation` contract, exact initial `contract_revision`, field-presence rules, availability states, provider derivation, no-fallback rules, feature expectations, and rollback contract;
- M39-WP2 source qualification, event immutability, payload baseline, temporal semantics, origin semantics, exclusions, ownership, provider independence, and reproducibility;
- M39-WP3 canonical class names, semantic boundaries, exactly-one-class rule, mixed-content treatment, correction classification, and extension rules;
- M39-WP4 Payload Meaning, Semantic Sufficiency, subject, temporal, provenance, uncertainty, absence, correction-lineage, compatibility, and extension rules; and
- every frozen identity, ingestion, ledger, portfolio, decision, Trust, authorization, execution, provider, runtime, storage, analytics, and Experience boundary.

### 12.2 M39-WP1 relationship

The M39-WP1 `MarketObservation` contract remains one frozen concrete contract for the M39-WP1 Market Price boundary.

This specification:

- MUST NOT add, remove, rename, reinterpret, or change the presence of any M39-WP1 field;
- MUST NOT change the exact initial `contract_revision` value;
- MUST NOT introduce relationship content into the M39-WP1 response;
- MUST NOT define an M39-WP1 observation identifier or relationship endpoint;
- MUST NOT change AVAILABLE, DEGRADED, UNAVAILABLE, or UNSUPPORTED semantics;
- MUST NOT change provider request derivation or the no-symbol-fallback rule;
- MUST NOT change Registry namespace or runtime `PRICE_PROVIDER` selection semantics;
- MUST NOT expose provider-specific relationship content;
- MUST NOT change feature-flag or rollback expectations; and
- MUST NOT make M39-WP1 assignment-compatible with execution evidence.

The constitutional vocabulary in M39-WP5 does not imply that any relationship is present in, required by, or permitted through M39-WP1.

### 12.3 No identity redefinition

M39-WP5 does not establish Observation identity.

In particular, it MUST NOT:

- expose an execution evidence reference as an Observation identity;
- treat provider symbols, source identifiers, payload values, timestamps, classes, or relationship roles as Observation identity;
- define identity syntax, equality, allocation, persistence, lookup, or resolution;
- infer that related observations are one identity; or
- transfer Asset Foundation identity authority to Market Intelligence.

### 12.4 Provider replacement

Equivalent source-established associations under canonical vocabulary MUST retain equivalent relationship meaning when the provider, relay, protocol, format, runtime, or storage mechanism changes.

Provider support for a relationship is an implementation concern and does not alter constitutional semantics.

## 13. Additive Extensibility

### 13.1 Extension admission test

A future Relationship Kind MAY be admitted only through separately approved governance and only when all of the following are established:

1. Every endpoint is an Observation Event admitted under M39-WP2.
2. Every endpoint preserves exactly one class under M39-WP3.
3. Every endpoint retains semantically sufficient Payload Meaning under M39-WP4.
4. The proposed relationship describes semantic association only.
5. The meaning is provider-neutral and implementation-neutral.
6. The meaning is not already represented by an existing Relationship Kind.
7. The meaning is non-overlapping and deterministically distinguishable.
8. Direction, endpoint roles, semantic scope, temporal meaning, provenance, uncertainty, and lifecycle implications are explicit where applicable.
9. The relationship preserves every endpoint’s identity, class, payload, immutability, and ownership.
10. The relationship introduces no calculation, inference, analytics, causality, prediction, recommendation, strategy, portfolio meaning, execution, transaction, truth, or authority.
11. Existing relationship meanings and existing consumer obligations remain unchanged.
12. No provider, runtime, transport, storage, graph, database, API, schema, serialization, or implementation is required to explain it.
13. M38 and M39-WP1 through M39-WP4 remain unchanged.
14. The extension receives separate constitutional authority before implementation or public exposure.

### 13.2 Extension prohibitions

A future extension MUST NOT:

- reinterpret, narrow, widen, rename, alias, supersede, invalidate, or carve meaning from an existing Relationship Kind;
- redefine Source, Origin, Event, Timestamp, Classification, Payload, or Observation identity;
- enter through a provider-private label, field, code, endpoint, or product;
- create an `OTHER`, `UNKNOWN`, generic `LINK`, opaque, or catch-all kind;
- make a concrete provider or mechanism mandatory;
- require existing consumers to understand the extension to preserve current behavior;
- infer relationship from similarity, chronology, co-location, shared asset, or differing values alone;
- transform association into causality, truth, preference, workflow, or action;
- widen M39-WP1 implicitly; or
- reopen any completed milestone or work package.

### 13.3 Forward compatibility

An implementation-independent consumer that understands existing Relationship Kinds MUST be able to preserve its existing interpretation when a separately governed future kind is added.

Forward compatibility MUST NOT require an existing kind to act as a fallback for an unknown future meaning.

An unrecognized or unratified relationship meaning remains unadmitted; it MUST NOT be coerced into the nearest existing kind.

## 14. Constitutional Invariants

The following rules are normative and cumulative.

### Semantic integrity

- **OR-01:** Every Observation Relationship MUST associate distinct Observation Events without changing any endpoint’s meaning.
- **OR-02:** Every Relationship Assertion MUST express exactly one canonical Relationship Kind.
- **OR-03:** Every endpoint MUST remain an immutable Observation Event with its own class, payload, temporal meaning, provenance, and uncertainty.
- **OR-04:** Relationship meaning MUST be limited to the narrowest source-established semantic scope.
- **OR-05:** Relationship MUST NOT manufacture evidence, cure an ineligible event, or substitute for Semantic Sufficiency.
- **OR-06:** When evidence is absent, insufficient, or ambiguous, a canonical relationship MUST NOT be asserted.

### Determinism and independence

- **OR-07:** Semantic Independence MUST be the default among distinct Observation Events.
- **OR-08:** Equivalent event meaning and source context under the same governed vocabulary MUST yield equivalent relationship disposition.
- **OR-09:** Shared subject, source, class, value, time, artifact, provider, or storage MUST NOT alone establish a relationship.
- **OR-10:** Relationship direction MUST be preserved when semantic and MUST NOT be inferred when absent.
- **OR-11:** A relationship MUST NOT be assumed symmetric, inverse, or transitive unless its canonical definition expressly establishes that property.
- **OR-12:** Chronology, correlation, containment, dependency, lineage, grouping, or cross-reference MUST NOT establish causation.

### Lifecycle integrity

- **OR-13:** Corrections, revisions, retractions, superseding claims, and later measurements MUST be new Observation Events.
- **OR-14:** Correction, Revision, Retraction, and Supersession MUST reflect only source-established meaning and MUST NOT be inferred from difference or recency.
- **OR-15:** Lifecycle relationships MUST preserve both earlier and later events and MUST NOT mutate, erase, merge, or silently replace either.
- **OR-16:** Supersession MUST NOT authorize a current, latest, effective, or preferred consumer projection.
- **OR-17:** Lifecycle relationship MUST NOT create a new Observation Class or change an endpoint’s class.
- **OR-18:** Relationship chains MUST NOT infer lineage, widen scope, or erase intermediate events.

### Boundary and ownership preservation

- **OR-19:** Market Intelligence MUST remain the sole semantic owner of Observation Relationships.
- **OR-20:** Relationship MUST NOT redefine or transfer ownership of Observation Source, Origin, Event, Timestamp, Classification, Payload, or Observation identity.
- **OR-21:** Relationship MUST NOT transfer identity, Registry, ingestion, ledger, portfolio, decision, Trust, authorization, execution, provider, runtime, storage, analytics, or Experience authority.
- **OR-22:** Relationship MUST remain evidence and MUST NOT become truth, quality, importance, suitability, currentness, preference, or authority to act.
- **OR-23:** Parent/Child and grouping MUST remain conceptual association and MUST NOT create object hierarchy, identity inheritance, ownership, cascade, or container semantics.
- **OR-24:** Cross-Reference MUST NOT import payload or imply dependency, endorsement, lifecycle, or causation.

### Provider and implementation neutrality

- **OR-25:** Relationship semantics MUST be provider-neutral, runtime-neutral, transport-neutral, storage-neutral, serialization-neutral, API-neutral, graph-neutral, and implementation-neutral.
- **OR-26:** Provider products, SDK types, field names, identifiers, endpoints, protocols, formats, graph structures, database structures, and runtime behavior MUST NOT enter canonical relationship vocabulary.
- **OR-27:** Concrete origin or relay identity MAY remain provenance but MUST NOT determine Relationship Kind.
- **OR-28:** Replacing a provider or mechanism MUST NOT change existing relationship meaning.
- **OR-29:** This specification MUST NOT define fields, identifiers, schemas, enums, edges, objects, APIs, serialization, persistence, traversal, transport, or implementation.

### Stability and forward compatibility

- **OR-30:** Existing Relationship Meaning MUST remain stable once canonically represented.
- **OR-31:** Future Relationship Kinds MUST be additive, non-overlapping, provider-neutral, and separately governed.
- **OR-32:** A future kind MUST NOT redefine an existing kind or enter through provider-private or catch-all vocabulary.
- **OR-33:** M38 and M39-WP1 through M39-WP4 MUST remain authoritative and unchanged.
- **OR-34:** No principle, relationship type, example, or conformance criterion SHALL imply implementation, runtime, storage, transport, provider, API, database, graph, or public-exposure authority.

## 15. Prohibited Interpretation

This specification MUST NOT be interpreted to permit any actor or future work package to:

- treat a relationship as part of an endpoint’s identity;
- merge related events into one event;
- mutate an event because another event is related;
- redefine Source, Origin, Timestamp, Classification, Payload, or Observation identity;
- infer a relationship from provider packaging, shared delivery, shared storage, or runtime order;
- infer correction, revision, retraction, or supersession from value difference or chronology;
- infer Semantic Dependency from citation, similarity, or shared context alone;
- infer Parent/Child from document or message co-location alone;
- use Related Observation as a generic fallback;
- treat relationship direction as temporal, causal, or preferential order;
- infer transitive, inverse, or symmetric relationships beyond their canonical definitions;
- infer asset identity, asset relationship, issuer relationship, predecessor, successor, or Registry lifecycle;
- infer ledger links, transaction reversals, accounting consequences, or truth;
- infer portfolio membership, exposure, valuation, performance, or risk;
- infer importance, quality, trust, correctness, currentness, freshness, conflict resolution, or preferred evidence;
- infer causality, correlation, explanation, prediction, recommendation, strategy, or action;
- authorize an alert, order, transaction, execution, workflow, approval, or human decision;
- create a graph, tree, hierarchy, DAG, event stream, event-sourcing contract, queue, schedule, or orchestration model;
- define a database link, foreign key, object reference, identifier, schema, enum, field, token, or serialization;
- define an endpoint, API, request, response, or transport;
- create provider mapping or provider-specific relationship behavior;
- create storage, caching, retention, replay, deletion, or traversal semantics;
- widen the M39-WP1 `MarketObservation` contract;
- expose execution evidence as Market Observation identity; or
- reopen M38 or M39-WP1 through M39-WP4.

## 16. Informative Examples

This section is informative. It illustrates the normative rules without authorizing implementation or public exposure.

### 16.1 Valid relationships

| Scenario | Relationship | Why valid |
| --- | --- | --- |
| A publisher explicitly corrects a numerical value in an earlier publication | Correction from the new event to the earlier event | The origin explicitly identifies error, target, and corrected scope |
| A statistical authority publishes an updated estimate for the same reference period and labels it a revision | Revision from the new event to the earlier event | The source establishes revision lineage without requiring an error finding |
| An origin withdraws an earlier announcement without supplying a replacement | Retraction from the new event to the earlier event | Retraction may preserve withdrawal without replacement truth |
| An origin declares a newly issued statement to replace an earlier statement for one stated section | Supersession from the new event to the earlier event for that scope | Replacement is explicit and scoped; both events remain immutable |
| A publication event explicitly cites an earlier qualifying publication event | Cross-Reference from the citing event to the cited event | Citation direction is source-established and does not imply endorsement |
| A qualifying composite publication event introduces a separately qualifying dividend event | Parent/Child from the publication context to the dividend event | Both endpoints qualify independently and containment is source-established |
| Several qualifying events are explicitly identified as parts of one source-defined release | Semantic Group Membership | The common release context is explicit and creates no composite class or payload |
| Two events are explicitly described by their origin as companion announcements without dependency | Related Observation | The material association is explicit, symmetric, and weaker than other kinds |
| A correction states that its meaning relies on the definitions published in an earlier qualifying event | Semantic Dependency and, if explicit, Cross-Reference as separate assertions | Each distinct relationship meaning is independently supported |

### 16.2 Invalid relationships

| Scenario | Invalid treatment | Resolution |
| --- | --- | --- |
| Two prices differ | Infer Correction or Revision | Preserve independent measurements unless the source establishes lineage |
| Two events concern the same asset | Infer Related Observation | Shared subject alone is insufficient |
| Two items arrive in one provider response | Infer Parent/Child or group membership | Provider packaging and delivery are not semantic association |
| A later event has a larger version number | Infer Supersession | Version notation alone does not establish replacement meaning |
| One publication cites another | Infer Semantic Dependency or endorsement | Preserve only Cross-Reference unless stronger meaning is explicit |
| A correction is considered more trustworthy | Mark the earlier event invalid | Trust assessment cannot mutate relationship or endpoint meaning |
| A source withdraws a claim | Delete the earlier event | Preserve the Retraction and historical event |
| Events occur close together | Infer causation | Chronology does not establish causality |
| A consumer wants a convenient collection | Create a Semantic Observation Group | Consumer convenience is not source-established grouping context |
| One event describes a successor instrument | Infer an Asset Foundation successor relationship | Observation evidence cannot adjudicate asset relationships |

### 16.3 Ambiguous cases and resolution

**Updated value without lifecycle language.** A source publishes a later value for the same subject. Unless the source identifies correction, revision, retraction, or supersession, the events remain independent later measurements.

**Correction that also replaces an earlier statement.** When the source independently establishes both error correction and scoped replacement, distinct Correction and Supersession assertions may coexist. They MUST NOT be collapsed into one ambiguous kind.

**Document with several fact classes.** A document containing price, dividend, and earnings facts is not automatically a parent event. Each qualifying Classifying Fact remains separate under M39-WP3. Parent/Child exists only if the containing publication context is itself an admitted event and the source meaning establishes containment.

**Series membership.** Events explicitly published as members of one named statistical series may share Semantic Group Membership. Membership does not establish ordering, revision, completeness, currentness, or preference.

**Reference required for terminology.** A new event that explicitly relies on definitions in an earlier admitted event may have Semantic Dependency and Cross-Reference as separate assertions. The new payload MUST still satisfy M39-WP4 Semantic Sufficiency.

**Common origin and subject.** Two events from the same origin about the same subject remain semantically independent absent a more specific source-established association.

**Source-reported causal statement.** A publication stating that one event caused another may preserve the attributed statement when otherwise admissible. WP5 does not convert that statement into a causal Relationship Kind or platform conclusion.

### 16.4 Boundary examples

**Portfolio use.** Portfolio Intelligence may consume related observations under existing authority. The relationship does not become a portfolio relationship and does not determine valuation, exposure, or action.

**Trust use.** Trust & Evaluation may assess whether correction lineage is credible. Its assessment remains separate and does not rewrite the relationship.

**Identity use.** An event may reference an existing canonical asset identity under prior governance. A relationship between observations never creates a relationship between assets.

**Execution use.** A market observation relationship does not establish executable price, eligibility, freshness acceptance, order readiness, or transaction authority.

## 17. Independent Review and Conformance

### 17.1 Conformance standard

A proposal conforms to M39-WP5 only when an independent reviewer can answer every applicable criterion below affirmatively from the proposal itself, without provider-private documentation, runtime behavior, storage inspection, implementation inference, or unstated convention.

| ID | Review criterion |
| --- | --- |
| AUTH-01 | M38 and M39-WP1 through M39-WP4 remain authoritative and unchanged |
| AUTH-02 | Market Intelligence remains sole semantic owner of Observation Relationships |
| AUTH-03 | No adjacent domain acquires new authority |
| EVT-01 | Every endpoint is already a distinct, immutable Observation Event |
| EVT-02 | No relationship changes endpoint identity, class, payload, time, provenance, uncertainty, or ownership |
| EVT-03 | Relationship does not make an ineligible event eligible or cure insufficient payload |
| SEM-01 | Each assertion has exactly one canonical Relationship Kind |
| SEM-02 | The relationship is the narrowest source-established provider-neutral meaning |
| SEM-03 | Direction and endpoint roles are explicit where semantically required |
| SEM-04 | Relationship scope is explicit and no wider than source meaning |
| SEM-05 | Insufficient or ambiguous evidence yields no admitted relationship |
| IND-01 | Semantic Independence is the default |
| IND-02 | Shared subject, source, class, value, time, artifact, or provider alone establishes no relationship |
| IND-03 | No relationship implies causality |
| LIF-01 | Correction, Revision, Retraction, and Supersession remain distinct |
| LIF-02 | Lifecycle relationships are source-established and not inferred from difference or recency |
| LIF-03 | Earlier and later events remain immutable and historically preserved |
| LIF-04 | Supersession creates no latest or preferred selection policy |
| LIF-05 | Relationship chains create no inferred transitive lineage or canonical version |
| GRP-01 | Parent/Child is conceptual containment only |
| GRP-02 | Semantic grouping creates no event, class, payload, order, hierarchy, or implementation container |
| REF-01 | Cross-Reference imports no payload and implies no dependency, endorsement, lifecycle, or causation |
| CLS-01 | Every endpoint retains exactly one M39-WP3 class |
| PAY-01 | Every endpoint retains M39-WP4 Semantic Sufficiency and immutable Payload Meaning |
| ID-01 | Observation identity is neither defined nor reinterpreted |
| ID-02 | No asset or execution identity authority is created |
| PRV-01 | Relationship meaning is independent of providers and mechanisms |
| PRV-02 | Provider terminology, identifiers, packaging, and behavior do not enter canonical vocabulary |
| EXT-01 | Future kinds are additive, non-overlapping, deterministic, and separately governed |
| EXT-02 | No catch-all or provider-private extension path exists |
| CMP-01 | M39-WP1 contract, availability, derivation, normalization, feature, and rollback semantics remain unchanged |
| CMP-02 | M39-WP2 source, event, time, origin, immutability, and provider-independence contracts remain unchanged |
| CMP-03 | M39-WP3 classes, one-class rule, mixed-content treatment, and correction classification remain unchanged |
| CMP-04 | M39-WP4 payload, temporal, provenance, uncertainty, absence, and correction-lineage semantics remain unchanged |
| IMP-01 | No graph, database, object, runtime, storage, transport, serialization, API, provider mapping, or implementation is designed |
| ACT-01 | No analytics, prediction, recommendation, strategy, portfolio, order, execution, transaction, or authority is introduced |

### 17.2 Required review evidence

Independent review MUST verify:

- constitutional consistency;
- deterministic terminology;
- provider and mechanism neutrality;
- immutable endpoint semantics;
- relationship-type distinctness;
- explicit correction, revision, retraction, and supersession boundaries;
- Semantic Independence and Causal Independence;
- conceptual-only parent, child, grouping, and cross-reference semantics;
- ownership preservation;
- compatibility with M38 and M39-WP1 through M39-WP4;
- additive forward extensibility;
- exclusion of implementation and public-contract decisions; and
- absence of architectural redesign.

### 17.3 Non-conformance

The proposal is non-conforming if any required criterion fails, if a Relationship Kind is ambiguous, if a relationship requires provider-private or runtime knowledge to interpret, or if it implies authority beyond semantic association.

Non-conformance MUST NOT be cured by:

- coercing meaning into a weaker or catch-all relationship;
- inferring missing source support;
- redefining a frozen term;
- changing an endpoint;
- relying on future implementation behavior; or
- widening this work package.

Conformance establishes constitutional relationship validity only. It does not approve a provider, implementation, runtime, graph, database, storage model, transport, serialization, schema, API, migration, feature activation, or public contract.

## 18. Constraints

All future work governed by this specification:

- MUST preserve provider-neutral semantic association;
- MUST preserve distinct and immutable Observation Events;
- MUST treat no relationship as the outcome when evidence is insufficient;
- MUST preserve Relationship Kind, direction, endpoint roles, semantic scope, provenance, and qualification where applicable;
- MUST keep relationships independent from Source, Classification, Payload, Observation identity, truth, causality, and consumer policy;
- MUST preserve every prior ownership boundary;
- MUST evolve only through additive, separately approved governance; and
- MUST NOT infer implementation or public-exposure authority from this specification.

## 19. Canonical Closure

M39-WP5 defines the constitutional semantic relationship boundary for future Market Observation work.

After ratification:

- relationships MAY describe only explicit provider-neutral semantic association among distinct Observation Events;
- Semantic Independence MUST remain the default;
- Causal Independence MUST remain absolute at the relationship boundary;
- correction, revision, retraction, and supersession MUST preserve immutable source-established lineage;
- parent, child, grouping, and cross-reference semantics MUST remain conceptual only;
- relationships MUST NOT redefine Source, Classification, Payload, or Observation identity;
- provider and mechanism changes MUST remain invisible to existing Relationship Meaning;
- future Relationship Kinds MUST be additive and separately governed;
- M38 and M39-WP1 through M39-WP4 MUST remain authoritative and unchanged; and
- this specification MUST NOT be treated as implementation or public-exposure authority.

Nothing in this specification reopens a completed milestone or authorizes implementation.
