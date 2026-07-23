# M39-WP6 — Market Observation Identity Specification

**Status:** Canonical specification candidate for independent constitutional review

**Authority:** M39-WP6

**Nature:** Normative constitutional identity specification

## 1. Purpose

This specification defines the constitutional semantic meaning of Observation Identity.

Observation Identity preserves the fact that one admitted Observation Event remains that same event across provider-neutral representations, relays, custody changes, and time. It distinguishes the continuity of an event from the content, classification, source, subject, relationships, or mechanisms associated with that event.

Observation Identity answers:

> Which one immutable Observation Event is semantically being denoted?

Observation Identity does not answer:

- what qualifies as an Observation Source;
- what kind of fact the event represents;
- what the event’s Payload Meaning contains;
- what relationships exist among distinct events;
- what canonical asset or external subject the event concerns;
- whether the event is true, trusted, current, important, actionable, or preferred;
- how the event is named, encoded, stored, located, compared, retrieved, or exposed; or
- what conclusion or action belongs to any consumer.

This specification establishes semantic obligations only. It does not authorize implementation, runtime adoption, persistence, provider integration, transport, public exposure, or amendment of an existing contract.

## 2. Authority and Compatibility

This specification is subordinate to the Platform Architecture and preserves all ratified governance through M39-WP5.

In particular:

- M38 remains complete and frozen;
- the M38 reserved market contribution and all M38 envelope, attachment, composition, availability, and ownership contracts remain unchanged;
- M39-WP1 remains complete and frozen;
- the M39-WP1 `MarketObservation` contract, public boundary, availability model, exact provider derivation, canonical normalization reuse, feature expectations, and execution separation remain unchanged;
- M39-WP2 remains authoritative for Observation Source eligibility and the meanings of Observation Event, Observation Payload, Observation Timestamp, and Observation Origin;
- M39-WP3 remains authoritative for Canonical Observation Classes, the Classifying Fact, the exactly-one-class rule, mixed-content treatment, and additive class admission;
- M39-WP4 remains authoritative for provider-neutral Payload Meaning, Semantic Sufficiency, temporal and provenance preservation, uncertainty, absence, Correction Lineage, and immutable correction treatment;
- M39-WP5 remains authoritative for Observation Relationship, Relationship Meaning, distinct relationship endpoints, Semantic Independence, lifecycle relationships, grouping, cross-reference, and Causal Independence;
- Market Intelligence remains the sole semantic owner of Market Observation and Observation Identity;
- Asset Foundation remains the sole owner of canonical asset identity and Registry adjudication;
- Connectivity & Ingestion retains ownership of external-fact ingestion toward ledger truth;
- all existing ledger, portfolio, decision, authorization, execution, provider, runtime, storage, analytics, Trust, and Experience boundaries remain unchanged; and
- Observation remains evidence, never identity authority for another domain, ledger truth, investment judgment, execution authority, or presentation authority.

This specification elaborates the identity of the immutable Observation Event established by M39-WP2. It SHALL NOT redefine Observation Source, Observation Event, Observation Payload, Observation Timestamp, Observation Origin, Observation Classification, Payload Meaning, Correction Lineage, Observation Relationship, or Relationship Meaning.

No general identity concept in this specification overrides a more specific frozen contract.

## 3. Scope

M39-WP6 defines:

- Observation Identity;
- provider-neutral identity principles;
- semantic identity and event continuity;
- identity boundaries and ownership;
- identity stability;
- semantic persistence;
- Identity Equivalence and Identity Distinctness;
- identity independence from adjacent semantics and mechanisms;
- compatibility with M38 and M39-WP1 through M39-WP5;
- additive identity extensibility;
- constitutional invariants;
- prohibited interpretations;
- informative examples; and
- objective independent-review criteria.

This specification defines semantic identity only.

### 3.1 Out of scope

The following are outside M39-WP6:

- identifier values, formats, syntax, allocation, namespaces, or lifecycle;
- database keys, records, constraints, indexes, or references;
- schemas, fields, enums, tokens, objects, or serialization;
- storage, persistence mechanisms, retention, replay, deletion, or restoration;
- APIs, endpoints, requests, responses, or public resources;
- runtime identity, process identity, memory identity, or object identity;
- provider identifiers, symbols, record keys, or message identifiers;
- identity derivation, matching, comparison, or equality algorithms;
- content fingerprints or mechanical identity construction;
- deduplication, merge, split, reconciliation, or record-linkage procedures;
- lookup, resolution, discovery, traversal, or indexing;
- ordering, version selection, current projection, or preferred-event selection;
- provider mappings, adapters, SDK behavior, or routing;
- transport, protocols, caching, queues, scheduling, or orchestration;
- authentication, authorization, approval, actor identity, or human authority;
- canonical asset identity, issuer identity, venue identity, or Registry adjudication;
- ledger identity, transaction identity, order identity, or portfolio identity;
- relationship implementation or graph structure;
- calculation, analytics, prediction, recommendation, strategy, or action;
- implementation of any kind; and
- public exposure of Observation Identity.

Naming an excluded mechanism to prohibit it does not authorize or design that mechanism.

## 4. Canonical Vocabulary

The terms in this section are normative.

### 4.1 Observation Identity

**Observation Identity** is the provider-neutral semantic continuity by which one admitted, immutable Observation Event is and remains that same event.

Observation Identity:

- belongs to exactly one Observation Event;
- preserves the event’s singularity across semantically faithful representations;
- remains stable for the lifetime of the event’s meaning;
- is distinct from the event’s Source, Origin, Classification, Payload, Timestamp, Semantic Subject, provenance, and Relationships;
- is distinct from any representation, reference, identifier, storage location, or runtime object;
- MUST NOT be derived solely from content equality or provider metadata; and
- MUST NOT create identity authority over any adjacent domain.

Observation Identity is a semantic property of an Observation Event. It is not an additional External Fact, Source-Reported Claim, Observation Payload, Observation Class, or Observation Relationship.

### 4.2 Identity Meaning

**Identity Meaning** is the constitutional assertion that a semantic reference or representation denotes one particular Observation Event and no other.

Identity Meaning contains only event sameness and continuity. It MUST NOT include:

- the event’s Claim Content;
- the event’s classification;
- the identity of its Semantic Subject;
- truth, quality, confidence, importance, freshness, or preference;
- lifecycle or relationship meaning;
- implementation representation; or
- authority to act.

### 4.3 Identity Basis

The **Identity Basis** is the complete attributable semantic evidence necessary to determine whether references or representations denote the same singular Observation Event or distinct Observation Events.

Identity Basis is event-relative and meaning-relative. It MAY include source-established event boundaries, claim occurrence, attribution, temporal meaning, provenance, and lifecycle context only to the extent necessary to preserve event singularity.

Identity Basis:

- MUST be provider-neutral;
- MUST preserve the event boundary established under M39-WP2 through M39-WP5;
- MUST NOT be reduced to one field, value, fixed tuple, content signature, provider record, or mechanical derivation;
- MUST NOT manufacture missing evidence;
- MUST NOT convert uncertainty into certainty; and
- does not prescribe an algorithm, representation, or identifier.

No individual semantic component establishes identity by itself unless separately ratified governance expressly makes that component sufficient. M39-WP6 establishes no such component.

### 4.4 Identity Continuity

**Identity Continuity** is the preservation of one Observation Identity while the same event is represented, relayed, normalized without meaning change, composed, assessed, or retained through constitutionally permitted boundaries.

Identity Continuity requires preservation of the event’s immutable meaning. It does not require one provider, one relay, one representation, one storage location, one runtime, or continuous availability.

Identity Continuity MUST NOT bridge two distinct Observation Events.

### 4.5 Identity Distinctness

**Identity Distinctness** is the constitutional condition in which two admitted Observation Events are not the same event and therefore do not share one Observation Identity.

Identity Distinctness applies when attributable semantic evidence establishes separate event boundaries, including:

- separately observed or reported claim occurrences;
- independently published events;
- corrections, revisions, retractions, superseding claims, and later measurements;
- distinct Classifying Facts admitted as separate events; or
- any other separately governed event boundary under M39-WP2 through M39-WP5.

Identity Distinctness does not imply disagreement, different payload content, different classes, different origins, different subjects, different quality, or a Relationship. It states only that the events are not one event.

### 4.6 Identity Equivalence

**Identity Equivalence** is the constitutional determination that two or more semantic references or semantically faithful representations co-refer to the same one Observation Event.

Identity Equivalence:

- MUST be supported by an unambiguous Identity Basis;
- MUST preserve one event boundary, one immutable event meaning, and one Observation Identity;
- MUST be reflexive, symmetric, and transitive as a property of co-reference;
- MUST NOT be inferred from equal or similar payloads alone;
- MUST NOT be inferred from shared source, origin, subject, class, time, relationship, provider, or delivery context alone;
- MUST NOT merge distinct Observation Events; and
- MUST NOT be treated as an Observation Relationship between events.

Identity Equivalence relates references or representations of one event. M39-WP5 relationships relate distinct events. The two concepts MUST NOT be conflated.

### 4.7 Semantic Equivalence

**Semantic Equivalence** is the condition in which distinct Observation Events preserve equivalent Payload Meaning or equivalent meaning within another separately governed semantic dimension.

Semantic Equivalence:

- MAY exist between Identity-Distinct events;
- does not establish Identity Equivalence;
- does not merge event histories, provenance, timestamps, uncertainty, or relationships;
- does not establish common origin or common occurrence; and
- does not select a canonical, preferred, or current event.

Two sources MAY independently report the same value with equivalent Payload Meaning while producing distinct Observation Events. Conversely, semantically faithful representations of one event MAY differ structurally while preserving Identity Equivalence.

### 4.8 Identity Stability

**Identity Stability** is the property that an admitted Observation Identity does not change, transfer, split, merge, or become another identity when surrounding conditions change.

Identity Stability MUST survive, without semantic change:

- provider or relay replacement;
- representation-preserving normalization;
- runtime or storage change;
- Experience composition;
- downstream assessment or use;
- later disagreement;
- correction, revision, retraction, supersession, or later measurement involving a distinct event; and
- addition or removal of Observation Relationships.

Identity Stability does not require permanent availability, retention, or one physical representation.

### 4.9 Semantic Persistence

**Semantic Persistence** is the continued validity of Identity Meaning through time, regardless of whether any particular representation, provider, runtime, or storage mechanism remains available.

Semantic Persistence:

- preserves that the event denoted remains the same historical event;
- preserves Identity Distinctness from every later event;
- MUST NOT be interpreted as a storage, retention, replay, backup, deletion, restoration, or availability requirement;
- MUST NOT create a permanent-access promise;
- MUST NOT permit identity reassignment when an event becomes unavailable; and
- MUST NOT make operational custody the owner of identity.

Semantic Persistence is conceptual continuity only.

### 4.10 Identity Independence

**Identity Independence** is the constitutional separation of Observation Identity from every semantic or operational dimension that does not itself establish event sameness.

Observation Identity is independent from:

- provider and relay identity;
- provider routing and availability;
- transport and serialization;
- runtime and storage;
- public or internal representation;
- canonical asset identity and Registry data;
- Observation Classification;
- Payload Meaning and value equality;
- Observation Relationships;
- trust, quality, validation, and disagreement;
- portfolio, ledger, decision, authorization, and execution state; and
- consumer context.

Independence does not erase attribution, temporal meaning, or provenance from the event. It prevents those dimensions from becoming identity shortcuts or acquiring identity ownership.

### 4.11 Identity Ambiguity

**Identity Ambiguity** is the constitutional condition in which available semantic evidence is insufficient or contradictory as to whether references or representations denote the same Observation Event.

Identity Ambiguity:

- MUST remain explicit;
- MUST NOT be resolved by guessing, fallback, content similarity, chronology, provider convention, or consumer preference;
- MUST NOT be coerced into Identity Equivalence;
- MUST NOT be coerced into Identity Distinctness without sufficient evidence;
- MUST NOT authorize event merge or mutation; and
- does not define a runtime status, response value, persistence state, or workflow.

Ambiguity is a review disposition, not a new Observation Identity or Observation Class.

### 4.12 Identity Compatibility

**Identity Compatibility** is the property that provider replacement, relay change, runtime change, storage change, representation change, additive extension, or new consumer use does not alter existing Identity Meaning, Identity Distinctness, or Identity Equivalence.

Identity Compatibility is semantic. It does not define source, binary, wire, schema, database, deployment, or API compatibility.

## 5. Identity Principles

### 5.1 Event-bounded

Observation Identity MUST be bounded by exactly one Observation Event admitted under M39-WP2.

One event MUST have one semantic identity. Two distinct events MUST NOT share one identity. Multiple faithful references or representations of one event MUST NOT create multiple semantic identities.

### 5.2 Semantic-first

Identity MUST be determined from the attributable semantic event boundary, not from a provider record, field, symbol, label, endpoint, message, object, storage location, or runtime path.

### 5.3 Provider-neutral

The same Observation Event MUST retain the same Identity Meaning when witnessed or relayed through different constitutionally eligible mechanisms, provided co-reference to that same event is unambiguous.

A provider change MUST NOT create a new event identity. A provider match MUST NOT prove one identity.

### 5.4 Immutable

Once an Observation Event is admitted, its Observation Identity MUST NOT change.

Identity MUST NOT be:

- reassigned to another event;
- transferred to a correction or revision;
- split because representations differ;
- merged because content matches;
- replaced by a later or preferred event; or
- retroactively changed by analysis, validation, or consumer use.

### 5.5 Deterministic

Equivalent Identity Basis under the same governed semantics MUST yield the same identity disposition.

Identity disposition MUST NOT depend on processing order, runtime state, provider availability, storage location, user, workspace, portfolio, consumer, or presentation.

### 5.6 Conservative equivalence

Identity Equivalence MUST be asserted only when co-reference to one event is unambiguous.

Absence of sufficient evidence MUST preserve Identity Ambiguity. Convenience, likely duplication, or a desire to consolidate MUST NOT lower the equivalence threshold.

### 5.7 Content non-derivation

Observation Identity MUST NOT be computed or inferred solely from:

- equal Payload Meaning;
- equal values;
- equal timestamps;
- equal subjects;
- equal classes;
- equal origin labels;
- equal provenance fragments; or
- any combination treated as a fixed identity recipe.

Material contradiction in immutable event meaning prevents an assertion of Identity Equivalence, but it does not by itself determine whether the evidence describes distinct events or an unresolved representation conflict.

### 5.8 Ownership-preserving

Observation Identity MUST remain Market Intelligence-owned and MUST NOT acquire or transfer:

- Asset Foundation identity authority;
- provider or source authority;
- ledger or accounting authority;
- portfolio authority;
- Trust or analytical authority;
- decision or action authority;
- authorization authority;
- execution authority; or
- runtime, storage, or Experience ownership.

### 5.9 Evidence, never verdict

Observation Identity states which event is denoted. It does not establish that the event’s claim is true, correct, validated, authoritative, important, current, or actionable.

### 5.10 Representation-free

Constitutional identity MUST remain understandable without specifying an identifier, field, object, schema, storage record, database key, API, serialized form, or runtime instance.

## 6. Identity Rules

### 6.1 Qualification precedes identity

A candidate MUST satisfy the complete M39-WP2 Observation Event boundary before it can possess Observation Identity.

Identity SHALL NOT:

- make an ineligible claim eligible;
- cure zero or multiple classification outcomes;
- make semantically insufficient payload sufficient;
- create an Observation Origin or Timestamp;
- establish a canonical Semantic Subject;
- create a Relationship; or
- authorize public exposure.

### 6.2 One event, one identity

Every admitted Observation Event MUST possess exactly one Observation Identity at the semantic boundary.

The following MUST remain distinct:

- one event and a correction of that event;
- one event and a revision of that event;
- one event and a retraction of that event;
- one event and a superseding event;
- one measurement and a later measurement;
- independently published claims, even when their content is equivalent; and
- independently qualifying Classifying Facts split from mixed source content.

### 6.3 Faithful representation

Multiple semantically faithful representations MAY preserve one Observation Identity only when they unambiguously denote the same admitted event.

Differences limited to representation, relay, transport, operational time, custody, or provider-neutral normalization MUST NOT create a new event identity when event co-reference and immutable meaning remain established.

This rule does not define representation equivalence or comparison mechanics.

### 6.4 Identity disposition

For a proposed comparison of semantic references or representations, constitutional review has exactly three dispositions:

1. **Identity Equivalent:** the evidence unambiguously establishes co-reference to one Observation Event.
2. **Identity Distinct:** the evidence unambiguously establishes separate Observation Events.
3. **Identity Ambiguous:** the evidence does not establish either outcome.

These are specification dispositions, not runtime statuses, response values, API errors, database states, or workflow outcomes.

### 6.5 Equivalence evidence

Identity Equivalence MAY be established only when the complete Identity Basis unambiguously preserves:

- one source-established or constitutionally admitted event boundary;
- one immutable event meaning;
- one attributable claim occurrence;
- compatible temporal meaning and provenance; and
- absence of a separately governed new-event condition.

This list defines semantic obligations, not an equality algorithm or fixed identity tuple.

No single item, and no mechanically chosen combination, is sufficient merely because it is available.

### 6.6 Distinctness evidence

Identity Distinctness MUST be preserved when the governed semantics establish:

- separate claim occurrences;
- separate publication or observation events;
- separate Classifying Facts;
- lifecycle lineage between an earlier and a new event;
- a later independent measurement; or
- another explicit event boundary under prior governance.

Identity Distinctness MUST NOT be inferred solely from different providers, relays, representations, receipt times, cache times, storage locations, or consumer contexts.

### 6.7 Ambiguity handling

When Identity Basis is insufficient or contradictory:

- Identity Equivalence MUST NOT be asserted;
- Identity Distinctness MUST NOT be asserted without independent support;
- no event MUST be merged, split, mutated, or replaced;
- no canonical identity fact MUST be manufactured;
- no provider-private convention or fallback MAY resolve the ambiguity; and
- any future resolution requires sufficient governed evidence without rewriting prior event meaning.

This specification does not define an ambiguity-resolution process.

### 6.8 Origin and relay

Observation Origin and relay provenance remain governed by M39-WP2 and M39-WP4.

The same origin MAY produce multiple Identity-Distinct events. Multiple relays MAY preserve references to one event. Origin or relay identity alone establishes neither equivalence nor distinctness.

Provider replacement, relay replacement, or provider unavailability MUST NOT change the identity of an already admitted event.

### 6.9 Temporal meaning

Observation Timestamp remains governed by M39-WP2 and M39-WP4.

The following rules apply:

- equal timestamps MUST NOT establish Identity Equivalence;
- different operational timestamps MUST NOT establish Identity Distinctness;
- receipt, retrieval, cache, storage, schedule, display, and processing time MUST NOT become event identity;
- materially incompatible source-established temporal meaning prevents unqualified Identity Equivalence; and
- a later source-established claim occurrence is a distinct event even when its value is unchanged.

Identity does not create ordering, versioning, freshness, or currentness.

### 6.10 Classification

Observation Classification remains governed by M39-WP3.

Classification:

- MUST NOT serve as Observation Identity;
- MUST NOT establish Identity Equivalence;
- MUST NOT establish Identity Distinctness by itself;
- MUST remain unchanged for one immutable event; and
- MUST remain attached independently to each Identity-Distinct event.

One identity MUST NOT denote events with materially conflicting canonical classifications. Such conflict is non-conforming or ambiguous evidence and MUST NOT be solved by changing identity semantics.

### 6.11 Payload

Observation Payload and Payload Meaning remain governed by M39-WP4.

Payload:

- MUST NOT serve as Observation Identity;
- MUST NOT establish Identity Equivalence through equal values or equivalent meaning alone;
- MUST remain immutable in meaning for one Observation Identity;
- MUST remain independently preserved for every Identity-Distinct event; and
- MUST NOT be copied, merged, or replaced to manufacture identity continuity.

Semantic Equivalence and Identity Equivalence MUST remain distinct.

### 6.12 Relationships

Observation Relationships remain governed by M39-WP5.

Relationship:

- associates Identity-Distinct Observation Events;
- MUST NOT serve as an endpoint’s Observation Identity;
- MUST NOT establish Identity Equivalence;
- MUST NOT merge endpoints;
- MUST NOT transfer identity through Parent/Child, Semantic Dependency, grouping, Cross-Reference, or lifecycle lineage; and
- MUST NOT change when an endpoint’s representation changes without semantic identity change.

If two references are Identity Equivalent, they denote one event and MUST NOT be modeled as two relationship endpoints merely because two representations exist.

## 7. Identity Boundaries and Boundary Matrix

| Boundary question | Inside Observation Identity | Outside Observation Identity | Required resolution |
| --- | --- | --- | --- |
| Which event is denoted? | One admitted immutable Observation Event | Claim truth, content interpretation, class, subject identity, or action | Preserve only event sameness and continuity |
| Are two representations of one event the same identity? | Identity Equivalence when co-reference is unambiguous | Structural equality, provider convention, or record matching | Use the complete semantic Identity Basis without defining mechanics |
| Are two equivalent claims the same event? | Not from equivalence alone | Content-based merge or consolidation | Preserve Semantic Equivalence separately from identity |
| Did a provider change create a new event? | No, when the same event remains unambiguously denoted | Provider-bound identity | Preserve provider-neutral Identity Continuity |
| Did a new claim occurrence create a new event? | Yes, when prior governance establishes a separate event boundary | Reuse of an earlier identity | Preserve Identity Distinctness |
| Is a correction the same event as the corrected event? | No | Mutation or version replacement | Preserve distinct identities and the M39-WP5 Correction Relationship |
| Is a revision the same event as the revised event? | No | One mutable versioned identity | Preserve distinct identities and Revision Relationship |
| Is a retraction the same event as the retracted event? | No | Historical erasure | Preserve distinct identities and Retraction Relationship |
| Is a superseding claim the same event as the earlier event? | No | Identity transfer or preferred-version selection | Preserve distinct identities and Supersession Relationship |
| Does a shared subject establish event identity? | No | Asset identity inference or event merge | Asset Foundation retains subject identity; events remain separately governed |
| Does a shared Relationship establish identity? | No | Endpoint merge or inherited identity | WP5 relationships remain among distinct events |
| Does storage preserve identity? | No semantic ownership transfer | Record identity, key identity, retention, or replay | Semantic Persistence remains independent of storage |
| Does an identifier define identity? | No representation choice | Syntax, allocation, equality, lookup, or namespace | Govern separately without changing Identity Meaning |
| Is an unavailable event no longer the same event? | No; availability does not alter Identity Meaning | Retention or access guarantee | Preserve semantic continuity without operational promise |
| Which event is current or preferred? | Nothing | Ranking, projection, conflict resolution, or consumer policy | Existing consumer or evaluation owner decides without changing identity |
| Is the event true or trustworthy? | Nothing | Validation, quality, confidence, or authority | Trust and validation owners assess without rewriting identity |

## 8. Ownership Model

Every concept has exactly one semantic owner. Reference, attribution, custody, normalization, comparison, consumption, or presentation does not create shared ownership.

| Concept or boundary | Canonical owner | Identity boundary |
| --- | --- | --- |
| Observation Identity and Identity Meaning | Market Intelligence | Sole semantic ownership under this specification |
| Observation Source, Event, Timestamp, and Origin semantics | Market Intelligence under M39-WP2 | Define eligible immutable event meaning without becoming identity substitutes |
| Observation Classification | Market Intelligence under M39-WP3 | Remains independent from Observation Identity |
| Observation Payload and Correction Lineage | Market Intelligence under M39-WP4 | Payload remains immutable per event; lineage establishes new-event relationships, not shared identity |
| Observation Relationships | Market Intelligence under M39-WP5 | Relate Identity-Distinct events without defining or transferring identity |
| External claim authorship | Observation Origin under M39-WP2 | Supplies attributable event evidence but does not own platform Observation Identity vocabulary |
| Canonical asset identity, Registry classification, and asset relationships | Asset Foundation | Observation Identity MUST NOT create, replace, merge, supersede, or adjudicate subject identity |
| Provider mapping custody | Asset Foundation under the frozen Registry boundary | Mapping addresses a provider and MUST NOT become Observation Identity |
| Provider interaction and translation | Existing Provider Layer | Provider references MAY preserve provenance but MUST NOT own or determine Observation Identity |
| External-fact ingestion toward ledger truth | Connectivity & Ingestion | Observation Identity does not create ingestion identity, reconciliation outcomes, or truth-path authority |
| Transactions and financial truth | Ledger & Accounting | Observation Identity MUST NOT create, link, merge, reverse, or supersede ledger or transaction identity |
| Portfolio facts and derivations | Portfolio Intelligence | Observation Identity creates no holding, position, valuation, exposure, or portfolio identity |
| Trust, quality, and conflict assessment | Trust & Evaluation or another frozen assessment owner | Assessment MAY consume identity evidence but MUST NOT mutate Identity Meaning |
| Analytics and derived results | The constitutional owner of each derived result | Similarity, clustering, correlation, and inferred sameness do not become Observation Identity |
| Investment conclusions and actions | Decision Intelligence and existing frozen action boundaries | Identity creates no prediction, recommendation, strategy, intent, approval, or execution |
| Authentication, authorization, approval, and actor identity | Existing non-domain authority boundaries | Observation Identity supplies no actor proof, permission, delegation, approval, or authority |
| Runtime and orchestration | Existing runtime and operational owners | Invocation and coordination MUST NOT own or redefine semantic identity |
| Storage and transport | Existing persistence and infrastructure owners | Custody MAY preserve a future representation but MUST NOT become identity authority |
| Experience composition | Experience Platform | Composition MAY render a future reference under separate authority but MUST NOT redefine identity |
| Future AI modules | Existing owner according to output meaning | Inferred identity, similarity, or consolidation remains outside canonical Observation Identity unless separately governed |

No row grants new authority. Prior ownership remains authoritative.

## 9. Identity Stability and Semantic Persistence

### 9.1 Stability across representations

One Observation Identity MUST remain stable across any semantically faithful representation that preserves the same event.

Representation differences MUST NOT create a new identity merely because they involve:

- different formatting;
- different provider-neutral normalized expression;
- different relay provenance;
- different transport;
- different custody;
- different operational timestamps;
- different presentation; or
- different consumer context.

This rule does not define which representations are mechanically equal.

### 9.2 Stability across later events

A later event MUST NOT inherit, replace, or absorb the identity of an earlier event.

This rule applies even when the later event:

- corrects the earlier event;
- revises the same measurement or term;
- retracts the earlier claim;
- supersedes the earlier claim;
- repeats identical content;
- is judged more accurate;
- is selected as current or preferred; or
- is related under M39-WP5.

The earlier and later identities remain distinct and stable.

### 9.3 Stability across assessment

Trust findings, validation outcomes, disagreement, conflict, quality judgments, or later evidence MUST NOT change Observation Identity.

An event found unreliable remains the same observed event. Identity does not imply endorsement and MUST NOT be revoked merely because the claim is rejected.

### 9.4 Semantic persistence without storage

Semantic Persistence requires only that Identity Meaning not change through time.

It does not require:

- a retained record;
- historical query support;
- backup or replay;
- permanent public reference;
- continuous availability;
- deletion prevention;
- restoration behavior; or
- any persistence technology.

Loss of access or custody MUST NOT authorize reuse or transfer of the event’s semantic identity.

### 9.5 No mutable current identity

Observation Identity MUST NOT denote “the latest observation,” “the current value,” “the preferred version,” or another mutable selection.

Such expressions describe a projection or consumer policy whose selected event is mutable. They are not one immutable Observation Identity.

Selection policy remains outside M39-WP6 and MUST NOT be encoded into Identity Meaning.

## 10. Identity Equivalence and Distinctness

### 10.1 Co-reference, not content comparison

Identity Equivalence means co-reference to one event. It does not mean that two events look alike or communicate the same claim.

Accordingly:

- one event expressed differently MAY preserve Identity Equivalence;
- two events expressed identically MAY remain Identity Distinct;
- one event relayed more than once MAY preserve one identity when co-reference is unambiguous; and
- two independent observations of the same unchanged state MUST remain distinct when their event boundaries are separate.

### 10.2 No fixed identity tuple

M39-WP6 establishes no fixed set of values whose equality proves Observation Identity.

In particular, no combination of:

- origin;
- relay;
- subject;
- class;
- value;
- timestamp;
- provenance;
- relationship;
- provider reference; or
- operational metadata

MAY be treated as a constitutional identity recipe.

These meanings MAY contribute to Identity Basis, but their relevance is governed by the event semantics and does not define an algorithm.

### 10.3 Lifecycle distinctness

Every correction, revision, retraction, superseding claim, and later measurement is a new Observation Event and therefore has an Identity Distinct from the earlier event.

Lifecycle relationships:

- MUST preserve all participating identities;
- MUST NOT transfer identity from earlier to later;
- MUST NOT make a later event a mutable version of the earlier event;
- MUST NOT erase earlier identity; and
- MUST NOT create a canonical current identity.

### 10.4 Mixed-content distinctness

When M39-WP3 requires mixed content to be split into independently qualifying Classifying Facts, each resulting Observation Event MUST have its own Identity Distinct from every other resulting event.

Shared artifact, origin, publication time, subject, or provenance MUST NOT merge those event identities.

### 10.5 Relay and republication

A relay that faithfully denotes the same source-established event MAY preserve Identity Equivalence when co-reference is unambiguous.

A republication, restatement, new publication occurrence, or independently attributable claim MAY constitute a distinct event even when content is unchanged.

The distinction MUST follow the governed event boundary. Provider packaging or delivery mechanics MUST NOT decide it.

### 10.6 Ambiguous duplication

Apparent duplication does not establish Identity Equivalence.

When two representations might denote one event but the Identity Basis is incomplete:

- they MUST NOT be merged;
- one MUST NOT replace the other;
- an identity MUST NOT be selected by preference;
- Semantic Equivalence MAY be preserved only if separately established; and
- Identity Ambiguity MUST remain explicit.

This specification does not define duplicate detection or resolution.

## 11. Identity Independence

### 11.1 Independence from Source and Origin

Observation Source and Observation Origin constrain event eligibility and attribution under M39-WP2. They do not themselves constitute Observation Identity.

One Origin MAY produce many Identity-Distinct events. One event MAY be relayed through multiple qualifying sources without acquiring multiple identities.

Changing attribution would materially affect event meaning and MUST NOT be used to silently preserve identity. An attribution conflict remains non-conforming or ambiguous; it MUST NOT be resolved by identity reassignment.

### 11.2 Independence from Classification

Classification identifies what kind of fact is represented. Identity identifies which event is denoted.

The same class contains many Identity-Distinct events. One event retains its class independently of how its identity is represented.

Classification MUST NOT be used as an identity namespace, identity value, or equivalence proof.

### 11.3 Independence from Payload

Payload preserves what the event means. Identity preserves which event it is.

Equivalent Payload Meaning across events MUST NOT collapse their identities. Identity Equivalence across faithful representations MUST NOT require byte-for-byte, field-for-field, or format equality.

Payload mutation is prohibited under M39-WP4 and MUST NOT be used to continue identity across materially changed event meaning.

### 11.4 Independence from Relationships

Relationship describes association among distinct events. Identity describes event singularity.

No Relationship Kind:

- makes endpoints one identity;
- transfers identity;
- creates identity inheritance;
- creates identity hierarchy;
- makes one endpoint an identity alias for another; or
- authorizes identity merge or replacement.

Parent/Child roles, grouping membership, Cross-Reference, Semantic Dependency, Correction, Revision, Retraction, and Supersession remain identity-neutral associations among distinct events.

### 11.5 Independence from Semantic Subject

The Semantic Subject MAY reference canonical identity governed by Asset Foundation. That subject identity is not Observation Identity.

Many Observation Events MAY concern one subject. One Observation Event MAY concern a source-established subject scope permitted by M39-WP4. Neither case transfers identity ownership.

`subject_asset_id`, where M39-WP1 applies, remains a reference to Registry-owned asset identity and MUST NOT be interpreted as Observation Identity.

### 11.6 Independence from provider and mechanism

Provider references, messages, symbols, routes, response objects, files, transport sessions, runtime objects, storage records, and presentation components MUST NOT define Observation Identity.

Their addition, replacement, movement, or removal MUST NOT alter Identity Meaning.

### 11.7 Independence from consumers and authority

Consumer use MUST NOT alter Observation Identity.

In particular:

- portfolio inclusion does not create or change identity;
- analytical similarity does not establish Identity Equivalence;
- trust assessment does not revoke identity;
- decision use does not make identity actionable;
- authorization does not validate identity meaning;
- execution use does not convert Observation Identity into execution evidence identity; and
- Experience composition does not acquire identity ownership.

## 12. Compatibility Requirements

### 12.1 Frozen compatibility

M39-WP6 MUST remain compatible with:

- M38 projection and contribution governance;
- M39-WP1 public resource, concrete `MarketObservation` contract, exact initial `contract_revision`, field-presence rules, availability states, provider derivation, no-fallback rules, feature expectations, and rollback contract;
- M39-WP2 source qualification, event immutability, payload baseline, temporal semantics, origin semantics, exclusions, ownership, provider independence, and reproducibility;
- M39-WP3 canonical class names, semantic boundaries, exactly-one-class rule, mixed-content treatment, correction classification, and extension rules;
- M39-WP4 Payload Meaning, Semantic Sufficiency, subject, temporal, provenance, uncertainty, absence, correction-lineage, compatibility, and extension rules;
- M39-WP5 Relationship Meaning, endpoint distinctness, lifecycle relationships, grouping, cross-reference, independence, compatibility, and extension rules; and
- every frozen identity, ingestion, ledger, portfolio, decision, Trust, authorization, execution, provider, runtime, storage, analytics, and Experience boundary.

### 12.2 M39-WP1 compatibility

The M39-WP1 `MarketObservation` contract remains one frozen concrete contract for the M39-WP1 Market Price boundary.

M39-WP1 does not expose or define Observation Identity. This specification:

- MUST NOT add, remove, rename, reinterpret, or change the presence of any M39-WP1 field;
- MUST NOT change the exact initial `contract_revision` value;
- MUST NOT introduce an Observation Identity field or reference into the M39-WP1 response;
- MUST NOT reinterpret `assetId`, `subject_reference`, or `subject_asset_id` as Observation Identity;
- MUST NOT reinterpret `contract_revision` as Observation Identity or event version identity;
- MUST NOT expose an execution evidence reference as Observation Identity;
- MUST NOT change AVAILABLE, DEGRADED, UNAVAILABLE, or UNSUPPORTED semantics;
- MUST NOT change provider request derivation or the no-symbol-fallback rule;
- MUST NOT change Registry namespace or runtime `PRICE_PROVIDER` selection semantics;
- MUST NOT expose provider-specific identity content;
- MUST NOT change feature-flag or rollback expectations; and
- MUST NOT make M39-WP1 assignment-compatible with execution evidence.

The constitutional vocabulary in M39-WP6 does not imply that Observation Identity is present in, required by, addressable through, or permitted by M39-WP1.

### 12.3 M39-WP2 through M39-WP4 compatibility

Observation Identity attaches only to one event already governed by M39-WP2 through M39-WP4.

It MUST NOT:

- alter event qualification;
- change event granularity;
- redefine Source or Origin;
- replace an Observation Timestamp;
- change a Canonical Observation Class;
- combine Classifying Facts;
- alter Payload Meaning or Semantic Sufficiency;
- manufacture subject identity;
- erase uncertainty or absence; or
- merge lifecycle events.

### 12.4 M39-WP5 compatibility

Every M39-WP5 Relationship Endpoint denotes one Identity-Distinct Observation Event.

WP6:

- MUST NOT redefine Relationship Endpoint representation;
- MUST NOT turn Identity Equivalence into a Relationship Kind;
- MUST NOT turn Relationship Meaning into identity evidence by itself;
- MUST NOT merge related endpoints;
- MUST NOT create identity inheritance through Parent/Child or grouping;
- MUST NOT turn lifecycle lineage into version identity; and
- MUST preserve every WP5 relationship independently of representation changes that preserve endpoint identity.

### 12.5 Provider replacement

Provider or relay replacement MUST remain an implementation event, not an Observation Identity event.

Equivalent representations of the same event retain Identity Meaning when co-reference is unambiguous. Provider replacement alone neither proves equivalence nor creates distinctness.

## 13. Additive Extensibility

### 13.1 Extension admission test

A future identity-semantic extension MAY be admitted only through separately approved governance and only when all of the following are established:

1. The extension concerns the semantic identity of an Observation Event admitted under M39-WP2.
2. It preserves exactly one class under M39-WP3.
3. It preserves immutable and semantically sufficient Payload Meaning under M39-WP4.
4. It preserves M39-WP5 Relationship Meaning and endpoint distinctness.
5. The proposed meaning is provider-neutral and implementation-neutral.
6. The meaning is not already represented by existing identity vocabulary.
7. The meaning is semantically distinct, deterministic, and non-conflicting.
8. It preserves one-event/one-identity, Identity Stability, Semantic Persistence, and conservative equivalence.
9. It preserves every existing ownership boundary.
10. It introduces no identifier syntax, allocation, namespace, storage, runtime, API, comparison algorithm, provider mapping, or public representation.
11. It introduces no calculation, analytics, prediction, recommendation, strategy, portfolio meaning, execution, transaction, truth, or authority.
12. Existing Identity Meaning and existing consumer obligations remain unchanged.
13. No provider or mechanism is required to explain the meaning.
14. M38 and M39-WP1 through M39-WP5 remain unchanged.
15. The extension receives separate constitutional authority before implementation or public exposure.

### 13.2 Extension prohibitions

A future extension MUST NOT:

- reinterpret, narrow, widen, rename, alias, supersede, invalidate, or carve meaning from Observation Identity;
- redefine Source, Origin, Event, Timestamp, Classification, Payload, Relationship, or Semantic Subject;
- enter through a provider-private identifier, field, code, endpoint, record, or product;
- create an `OTHER`, `UNKNOWN`, provisional, opaque, or catch-all identity kind;
- make a provider, relay, runtime, storage mechanism, transport, or representation mandatory;
- define a concrete identifier, key, field, schema, object, or API;
- define an equality, matching, merge, split, or deduplication algorithm;
- use semantic equivalence as identity equivalence;
- create mutable latest, current, or preferred identity;
- transfer Asset Foundation or adjacent-domain identity authority;
- widen M39-WP1 implicitly; or
- reopen any completed milestone or work package.

### 13.3 Forward compatibility

Future identity-semantic vocabulary MUST be additive and MUST preserve all existing identity dispositions.

An existing consumer MUST NOT be required to reinterpret an Observation Identity when a separately governed future semantic distinction is added.

Unrecognized or unratified identity meaning remains unadmitted. It MUST NOT be coerced into Identity Equivalence, Identity Distinctness, or a catch-all identity category.

## 14. Constitutional Invariants

The following rules are normative and cumulative.

### Event singularity and stability

- **OI-01:** Every admitted Observation Event MUST have exactly one semantic Observation Identity.
- **OI-02:** One Observation Identity MUST denote exactly one immutable Observation Event.
- **OI-03:** Identity MUST remain stable and MUST NOT change, transfer, split, merge, or become another identity.
- **OI-04:** Multiple faithful representations of one event MUST NOT create multiple semantic identities.
- **OI-05:** Distinct Observation Events MUST NOT share one Observation Identity.
- **OI-06:** Correction, Revision, Retraction, Supersession, and later-measurement events MUST remain Identity Distinct from every earlier event.

### Equivalence and ambiguity

- **OI-07:** Identity Equivalence MUST mean co-reference to one Observation Event and MUST NOT mean content similarity.
- **OI-08:** Identity Equivalence MUST require an unambiguous complete Identity Basis.
- **OI-09:** Equal payload, value, time, subject, class, origin, provenance, provider, or relationship MUST NOT alone establish Identity Equivalence.
- **OI-10:** Semantic Equivalence MUST NOT collapse Identity-Distinct events.
- **OI-11:** Identity Ambiguity MUST remain explicit and MUST NOT be resolved by guessing, fallback, convention, or consumer preference.
- **OI-12:** Identity disposition MUST be deterministic under equivalent governed evidence.

### Semantic persistence and independence

- **OI-13:** Identity Meaning MUST remain valid through time without implying storage, retention, replay, restoration, or availability.
- **OI-14:** Provider, relay, runtime, transport, storage, serialization, representation, and consumer changes MUST NOT alter Identity Meaning.
- **OI-15:** Observation Identity MUST remain independent from Source, Origin, Classification, Payload, Relationship, Semantic Subject, trust, analytics, portfolio, ledger, authorization, execution, and Experience state.
- **OI-16:** Operational timestamps, receipt order, storage order, and processing order MUST NOT become event identity.
- **OI-17:** Observation Identity MUST NOT denote a mutable latest, current, preferred, or effective selection.
- **OI-18:** Loss of availability or custody MUST NOT authorize identity reuse, reassignment, or transfer.

### Ownership and authority

- **OI-19:** Market Intelligence MUST remain the sole semantic owner of Observation Identity.
- **OI-20:** Observation Identity MUST NOT transfer canonical asset identity or Registry authority from Asset Foundation.
- **OI-21:** Observation Identity MUST NOT transfer provider, ingestion, ledger, portfolio, Trust, analytics, decision, authorization, execution, runtime, storage, or Experience authority.
- **OI-22:** Observation Identity MUST remain evidence-bounded and MUST NOT become truth, quality, importance, suitability, currentness, preference, or authority to act.
- **OI-23:** Reference, relay, custody, normalization, assessment, consumption, or rendering MUST NOT transfer identity ownership.

### Prior-contract preservation

- **OI-24:** Observation Identity MUST NOT redefine Observation Source, Event, Timestamp, Origin, Classification, Payload, Relationship, or Semantic Subject.
- **OI-25:** Identity Equivalence MUST NOT become an M39-WP5 Relationship Kind.
- **OI-26:** M39-WP5 relationships MUST remain among Identity-Distinct endpoints and MUST NOT transfer or merge identity.
- **OI-27:** `assetId`, `subject_reference`, and `subject_asset_id` MUST remain subject-addressing or subject-reference semantics and MUST NOT become Observation Identity.
- **OI-28:** An execution evidence reference MUST NOT be exposed as Observation Identity.
- **OI-29:** M39-WP1 contract, availability, derivation, normalization, feature, and rollback semantics MUST remain unchanged.

### Implementation neutrality and forward compatibility

- **OI-30:** Observation Identity MUST be provider-neutral, implementation-neutral, runtime-neutral, storage-neutral, transport-neutral, serialization-neutral, API-neutral, and representation-neutral.
- **OI-31:** Provider fields, symbols, record references, SDK concepts, endpoints, protocols, database structures, and runtime objects MUST NOT enter canonical identity vocabulary.
- **OI-32:** This specification MUST NOT define identifiers, formats, fields, schemas, keys, objects, APIs, persistence, lookup, resolution, comparison mechanics, or implementation.
- **OI-33:** Future identity-semantic extensions MUST be additive, deterministic, non-conflicting, and separately governed.
- **OI-34:** A future extension MUST NOT enter through provider-private, mutable, provisional, or catch-all identity vocabulary.
- **OI-35:** M38 and M39-WP1 through M39-WP5 MUST remain authoritative and unchanged.
- **OI-36:** No principle, example, or conformance criterion SHALL imply implementation, runtime, storage, transport, provider, API, identifier, database, or public-exposure authority.

## 15. Prohibited Interpretation

This specification MUST NOT be interpreted to permit any actor or future work package to:

- treat Observation Identity as an identifier value or format;
- define identifier syntax, allocation, namespace, lookup, or resolution;
- derive identity mechanically from event content or metadata;
- define database keys, records, constraints, indexes, or links;
- define schemas, fields, enums, objects, tokens, or serialization;
- define APIs, endpoints, requests, responses, or public resources;
- define runtime, storage, caching, retention, replay, deletion, restoration, or migration behavior;
- define provider IDs, mappings, adapters, SDK behavior, routes, or fallbacks;
- define identity matching, comparison, equality, deduplication, merge, split, or reconciliation algorithms;
- infer Identity Equivalence from equal payload, value, time, origin, subject, class, provenance, provider, or Relationship alone;
- merge Identity-Distinct events because they are semantically equivalent;
- split one identity because faithful representations differ;
- transfer an earlier identity to a correction, revision, retraction, superseding claim, or later measurement;
- erase or revoke an event identity because the claim is later rejected or withdrawn;
- create a mutable latest, current, preferred, effective, or canonical-version identity;
- use receipt, retrieval, cache, storage, processing, or display time as event identity;
- treat `assetId`, `subject_reference`, `subject_asset_id`, a provider symbol, or a source reference as Observation Identity;
- infer asset identity, issuer identity, asset relationship, predecessor, successor, or Registry lifecycle;
- treat an Observation Relationship as identity, alias, inheritance, or merge authority;
- expose execution evidence identity or reference as Observation Identity;
- infer ledger, transaction, order, portfolio, actor, workspace, or authorization identity;
- infer truth, correctness, quality, confidence, importance, freshness, preference, causality, or action;
- create prediction, recommendation, strategy, intent, order, execution, transaction, or workflow authority;
- transfer identity ownership through provider custody, storage, runtime, analysis, or Experience composition;
- widen the M39-WP1 `MarketObservation` contract; or
- reopen M38 or M39-WP1 through M39-WP5.

## 16. Informative Examples

This section is informative. It illustrates the normative rules without authorizing implementation or public exposure.

### 16.1 Valid identity interpretation

| Scenario | Identity interpretation | Reason |
| --- | --- | --- |
| The same admitted publication event is faithfully relayed through two independent mechanisms with unambiguous co-reference | One Observation Identity | Relay difference does not create a new event |
| One admitted event is expressed in two provider-neutral representations without meaning change | One Observation Identity | Representation differs while event continuity remains |
| Two independent venues report the same price at the same stated time | Two identities unless the evidence establishes one shared event | Equal content and time do not establish co-reference |
| An origin publishes a corrected value | The correction and earlier event have distinct identities | M39-WP2 and M39-WP4 require a new immutable event |
| An origin republishes unchanged content as a new attributable publication occurrence | Distinct identities | A new publication occurrence is a new event |
| An event becomes unavailable from its former relay | Identity Meaning remains unchanged | Availability and custody do not define semantic identity |
| A later event is selected by a consumer as current | Earlier and later identities remain unchanged | Selection policy is outside identity |
| Two representations might be duplicates but provenance is incomplete | Identity Ambiguous | Insufficient evidence cannot be coerced into equivalence or distinctness |

### 16.2 Invalid identity interpretation

| Scenario | Invalid treatment | Resolution |
| --- | --- | --- |
| Two payloads have equal values | Declare Identity Equivalence | Preserve Semantic Equivalence only if established; identity requires co-reference |
| Two events have the same subject and class | Merge identities | Shared subject and class are insufficient |
| A provider assigns the same record reference | Treat the provider reference as canonical identity | Provider evidence cannot define Observation Identity |
| A correction replaces an earlier value | Reuse the earlier identity for the correction | Preserve distinct identities and Correction Relationship |
| A newer event is preferred | Rename it as the current identity | Keep selection separate from immutable identity |
| Two relays format one event differently | Create two identities from structural difference | Preserve one identity when co-reference and meaning are unambiguous |
| A retracted claim is considered false | Delete or revoke its identity | Preserve the historical event and distinct Retraction event |
| A Parent/Child relationship exists | Inherit parent identity into child | Relationship roles do not transfer identity |
| A record is moved between storage systems | Create a new event identity | Storage change is identity-neutral |
| Identity evidence conflicts | Guess using provider priority | Preserve Identity Ambiguity |

### 16.3 Equivalence and distinctness examples

**Same claim, multiple relays.** Two relays explicitly and unambiguously denote one source-issued publication occurrence. They may preserve one Observation Identity. Relay provenance remains distinct from identity.

**Same value, repeated observation.** A venue reports the same price in two separately observed moments. The payload values may be semantically equivalent, but the event occurrences and identities are distinct.

**Same timestamp, independent claims.** Two origins publish the same value with the same stated time. Neither shared time nor content establishes one event identity.

**Representation-preserving normalization.** One event’s source meaning is expressed through canonical vocabulary without semantic change. Normalization does not create a new Observation Identity.

**Materially conflicting representations.** Two representations claimed to denote one event disagree about material immutable meaning. Identity Equivalence cannot be asserted. The conflict remains non-conforming or Identity Ambiguous until governed evidence resolves it.

**Correction lineage.** A corrected event, correction event, and any later revision each retain separate identities. Relationships preserve lineage without creating versions of one mutable identity.

**Mixed-content publication.** A source artifact contains several independently qualifying Classifying Facts. Each admitted Observation Event has a distinct identity even when origin, artifact, and publication time are shared.

### 16.4 Boundary examples

**Asset identity.** Many Observation Events may reference one Registry-owned asset. None shares the asset’s identity, and `subject_asset_id` remains a subject reference only.

**Relationship identity.** A Cross-Reference or Parent/Child relationship connects distinct event identities. It does not create aliases or identity inheritance.

**Trust assessment.** Trust & Evaluation may determine that an event is unreliable. The assessment does not revoke or change which historical event was observed.

**Portfolio use.** Portfolio Intelligence may consume one observation rather than another. Consumption and selection do not alter event identity.

**Execution boundary.** An Observation Identity does not become an execution quote, executable evidence reference, order identity, or transaction identity.

**Semantic persistence.** A former representation may no longer be retained or accessible. The constitutional meaning that the historical event was one particular event does not become available for reassignment.

## 17. Independent Review and Conformance

### 17.1 Conformance standard

A proposal conforms to M39-WP6 only when an independent reviewer can answer every applicable criterion below affirmatively from the proposal itself, without provider-private documentation, runtime behavior, storage inspection, implementation inference, or unstated convention.

| ID | Review criterion |
| --- | --- |
| AUTH-01 | M38 and M39-WP1 through M39-WP5 remain authoritative and unchanged |
| AUTH-02 | Market Intelligence remains sole semantic owner of Observation Identity |
| AUTH-03 | Asset Foundation and every adjacent owner retain prior identity authority |
| EVT-01 | Observation Identity denotes exactly one admitted immutable Observation Event |
| EVT-02 | Every distinct Observation Event has an Identity Distinct from every other event |
| EVT-03 | Corrections, revisions, retractions, superseding claims, and later measurements retain distinct identities |
| EVT-04 | Multiple faithful representations of one event do not create multiple identities |
| SEM-01 | Identity Meaning contains event sameness only |
| SEM-02 | Identity Basis is semantic, complete, provider-neutral, and not a fixed tuple or algorithm |
| SEM-03 | Identity Stability survives provider, representation, custody, assessment, and relationship change |
| SEM-04 | Semantic Persistence creates no storage or availability requirement |
| EQV-01 | Identity Equivalence means unambiguous co-reference to one event |
| EQV-02 | Semantic Equivalence remains distinct from Identity Equivalence |
| EQV-03 | Equal content, source, subject, class, time, provider, or relationship alone proves no identity |
| EQV-04 | Ambiguity remains explicit and causes no merge, split, or guessed disposition |
| IND-01 | Identity remains independent from Source, Classification, Payload, Relationship, and Semantic Subject |
| IND-02 | Identity remains independent from provider, runtime, storage, transport, serialization, and representation |
| IND-03 | Identity creates no truth, trust, importance, currentness, preference, or action authority |
| OWN-01 | Subject identity remains owned by Asset Foundation |
| OWN-02 | Provider, ledger, portfolio, Trust, decision, authorization, execution, runtime, storage, and Experience boundaries remain unchanged |
| REL-01 | M39-WP5 relationships remain among Identity-Distinct endpoints |
| REL-02 | Identity Equivalence is not an Observation Relationship |
| REL-03 | No relationship transfers, merges, aliases, inherits, or replaces identity |
| WP1-01 | M39-WP1 gains no identity field, identifier, reference, or public behavior |
| WP1-02 | `assetId`, `subject_reference`, `subject_asset_id`, and `contract_revision` are not Observation Identity |
| WP1-03 | Execution evidence references remain structurally and semantically separate |
| PRV-01 | Concrete provider identity and provider records do not determine Observation Identity |
| PRV-02 | Provider or relay replacement does not alter existing Identity Meaning |
| EXT-01 | Future identity semantics are additive, deterministic, non-conflicting, and separately governed |
| EXT-02 | No provider-private, provisional, mutable, or catch-all identity extension exists |
| IMP-01 | No identifier format, schema, key, storage, API, runtime, comparison algorithm, or implementation is defined |
| ACT-01 | No analytics, prediction, recommendation, strategy, portfolio, order, execution, transaction, or authority is introduced |

### 17.2 Required review evidence

Independent review MUST verify:

- constitutional consistency;
- deterministic and provider-neutral terminology;
- one-event/one-identity singularity;
- immutable identity stability;
- semantic persistence without storage assumptions;
- strict separation of Identity Equivalence and Semantic Equivalence;
- conservative ambiguity treatment;
- new-event identity for every lifecycle event;
- independence from Source, Classification, Payload, Relationship, and Semantic Subject;
- ownership preservation;
- compatibility with M38 and M39-WP1 through M39-WP5;
- additive forward extensibility;
- exclusion of identifiers, implementation, and public-contract decisions; and
- absence of architectural redesign.

### 17.3 Non-conformance

A proposal is non-conforming if any required criterion fails, if identity depends on provider or mechanism behavior, if semantic equivalence is treated as event sameness, or if implementation knowledge is required to interpret Identity Meaning.

Non-conformance MUST NOT be cured by:

- guessing identity;
- applying provider precedence;
- matching content mechanically;
- merging or splitting events;
- transferring identity across lifecycle relationships;
- redefining a frozen term;
- relying on future implementation behavior; or
- widening this work package.

Conformance establishes constitutional identity validity only. It does not approve an identifier, provider, runtime, storage model, transport, serialization, schema, database, API, migration, feature activation, or public contract.

## 18. Constraints

All future work governed by this specification:

- MUST preserve one semantic identity for one immutable Observation Event;
- MUST preserve Identity Distinctness among distinct events;
- MUST assert Identity Equivalence only for unambiguous co-reference;
- MUST keep Semantic Equivalence distinct from Identity Equivalence;
- MUST preserve Identity Ambiguity when evidence is insufficient;
- MUST preserve Identity Stability and Semantic Persistence;
- MUST keep identity independent from Source, Classification, Payload, Relationship, Semantic Subject, provider, runtime, storage, and consumer policy;
- MUST preserve every prior ownership boundary;
- MUST evolve only through additive, separately approved governance; and
- MUST NOT infer implementation or public-exposure authority from this specification.

## 19. Canonical Closure

M39-WP6 defines the constitutional semantic identity boundary for future Market Observation work.

After ratification:

- every admitted Observation Event MUST have one immutable semantic identity;
- Identity Meaning MUST denote only event sameness and continuity;
- Identity Equivalence MUST mean unambiguous co-reference to one event;
- Semantic Equivalence MUST NOT collapse distinct event identities;
- corrections, revisions, retractions, superseding claims, and later measurements MUST retain distinct identities;
- Identity Ambiguity MUST remain explicit and MUST NOT authorize guessing or merge;
- semantic identity MUST persist without creating storage, runtime, identifier, or availability requirements;
- Source, Classification, Payload, Relationship, Semantic Subject, and adjacent-domain identity MUST remain independent;
- provider and mechanism changes MUST remain invisible to existing Identity Meaning;
- future identity semantics MUST be additive and separately governed;
- M38 and M39-WP1 through M39-WP5 MUST remain authoritative and unchanged; and
- this specification MUST NOT be treated as implementation or public-exposure authority.

Nothing in this specification reopens a completed milestone or authorizes implementation.
