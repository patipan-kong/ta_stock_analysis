# M39-WP2 — Market Observation Source Boundary Specification

**Status:** Canonical specification candidate for independent review

**Milestone:** M39 — Canonical Asset Market Observation

**Document role:** Constitutional source-boundary contract for Market Observation

**Normative language:** `MUST`, `MUST NOT`, `SHALL`, `SHALL NOT`, `MAY`, and `SHOULD` are normative. Informative examples are explicitly identified and are non-normative.

## 1. Purpose

This specification defines the constitutional boundary of every source that may participate in the Market Observation subsystem.

It establishes:

- what qualifies as an Observation Source;
- what an Observation Source may assert;
- the boundary between externally observable facts and platform-owned derivation, judgment, action, or state;
- deterministic semantic ownership;
- provider and mechanism independence; and
- the rules by which future observation classes may be introduced without changing existing observation semantics.

This specification governs source eligibility and source meaning only. It does not admit a source into runtime use, define an integration, or authorize a new Market Observation contract.

## 2. Authority and Compatibility

This specification is subordinate to the Platform Architecture and preserves all ratified governance through M39-WP1.

In particular:

- M38 remains complete and frozen;
- the M38 reserved market contribution and all M38 envelope, attachment, composition, availability, and ownership contracts remain unchanged;
- M39-WP1 remains complete and frozen;
- the M39-WP1 `MarketObservation` contract, public boundary, availability model, exact provider derivation, feature expectations, and execution separation remain unchanged;
- Market Intelligence remains the sole semantic owner of Market Observation;
- Asset Foundation remains the sole owner of canonical asset identity and Registry adjudication;
- existing execution, portfolio, ledger, authorization, search, provider, analytics, and Experience contracts remain unchanged; and
- Observation remains evidence, not ledger truth, identity authority, investment judgment, execution authority, or presentation authority.

The source categories identified by this specification are constitutionally eligible categories only. Their inclusion SHALL NOT imply current support, runtime enablement, provider capability, public exposure, persistence, or admission into the M39-WP1 `MarketObservation` contract.

## 3. Scope

M39-WP2 defines:

- canonical source-boundary vocabulary;
- the qualification test for an Observation Source;
- included source categories and their fact-bearing limits;
- explicit exclusions from the Observation domain;
- provider-independence rules;
- source, payload, origin, and temporal responsibility boundaries;
- ownership and boundary matrices;
- constitutional invariants;
- forward-compatible extension rules;
- non-normative classification examples; and
- conformance requirements for future source specifications.

M39-WP2 does not define implementation, runtime behavior, provider integration, APIs, storage, transport, or orchestration.

## 4. Canonical Definitions

### 4.1 Observation Source

An **Observation Source** is an external witness that can originate or relay an attributable claim about an externally observable state, event, publication, or measurement.

An Observation Source is defined by the kind of external fact it can witness, not by a vendor, product, protocol, data format, software library, deployment, or storage location.

An Observation Source:

- MUST be external to the platform domain that consumes its claim;
- MUST be capable of producing at least one qualifying Observation Event under §5;
- MUST expose an attributable Observation Origin;
- MUST preserve the temporal meaning of the claim;
- MUST NOT possess platform identity, accounting, portfolio, decision, authorization, or execution authority; and
- MUST NOT become a semantic dependency merely because its provenance is retained.

A source may publish both qualifying and non-qualifying material. Eligibility attaches only to the fact-bearing subset that satisfies §5; it does not attach indiscriminately to every output of the source.

### 4.2 Observation Event

An **Observation Event** is one immutable, attributable representation of a Source-Reported Claim about a qualifying External Fact, with explicit temporal meaning.

An Observation Event represents what was externally observed or reported. It does not establish that the claim is canonical identity, ledger truth, an approved interpretation, or authority to act.

Once represented, the meaning of an Observation Event MUST NOT change. A correction, revision, retraction, or later measurement is a new Observation Event and SHALL NOT rewrite the earlier event.

Logical immutability does not require or prescribe persistence. A current projection MAY identify a later event without mutating the meaning of an earlier one.

### 4.3 Observation Payload

An **Observation Payload** is the canonical, provider-neutral fact content carried by an Observation Event.

It states only what the external origin observed, measured, declared, published, or reported, together with qualifications necessary to preserve that meaning.

An Observation Payload:

- MUST use platform-owned semantic vocabulary;
- MUST preserve source uncertainty, absence, and qualification;
- MUST NOT contain provider packaging or transport semantics;
- MUST NOT contain platform calculations, derived indicators, predictions, recommendations, strategies, or action instructions; and
- MUST NOT transfer semantic ownership from any adjacent domain.

The term Observation Payload in this specification is conceptual. It does not redefine the payload shape frozen by M39-WP1 or authorize a new public representation.

### 4.4 Observation Timestamp

An **Observation Timestamp** is the time associated with the external fact or source claim, accompanied by semantics that identify what the time means.

Depending on the observation class, that meaning may be when a state was observed, an event occurred, a value became effective, or a publication was issued. Distinct temporal meanings MUST remain distinct.

An Observation Timestamp:

- MUST be attributable to the Observation Event’s source meaning;
- MUST NOT be inferred from retrieval, receipt, cache, storage, scheduling, or display time;
- MUST NOT collapse multiple materially different event dates into one ambiguous time; and
- MUST remain absent or explicitly qualified when the source does not establish it.

Retrieval, receipt, and cache times are provenance or operational context. They are not Observation Timestamps merely because they are available.

### 4.5 Observation Origin

An **Observation Origin** is the external entity, venue, authority, publisher, instrument, or measurement process responsible for a Source-Reported Claim about an External Fact.

Observation Origin is semantic provenance. It is distinct from:

- the subject about which the claim is made;
- a vendor or intermediary that relays the claim;
- an adapter or SDK that translates it;
- a protocol or file that transports it; and
- a platform component that receives or stores it.

An Observation Origin MUST be attributable without becoming a behavioral branch in the core model. Concrete origin or relay identities MAY be retained as provenance values, but MUST NOT define observation semantics.

### 4.6 External Fact and Source-Reported Claim

An **External Fact** is an observable state or occurrence outside the platform. A **Source-Reported Claim** is an attributable external statement about such a fact.

Observation represents evidence faithfully; it does not convert testimony into unquestionable truth. Where correctness is uncertain, the canonical representation MUST preserve that uncertainty.

The externally observable fact that a source published a value or statement MAY qualify even when the source created that value using its own methodology. The Observation domain records the attributed source claim; it MUST NOT reproduce the source’s derivation, endorse it as platform judgment, or silently reinterpret it as a platform-calculated result.

## 5. Observation Source Qualification Test

A source qualifies as an Observation Source only for outputs satisfying every rule below.

| Qualification | Normative test |
| --- | --- |
| Externality | The claim MUST originate outside the consuming platform domain. Platform state or output SHALL NOT become external merely because it is exposed through a boundary. |
| Observability | The claim MUST concern a state, event, publication, or measurement that was externally observable. A desired action, hypothetical outcome, or platform opinion does not qualify. |
| Attribution | An Observation Origin MUST be identifiable. Anonymous or untraceable content MUST NOT become canonical Observation evidence. |
| Temporal meaning | The claim MUST carry an Observation Timestamp or an explicit qualification that the source did not establish one. |
| Representational fidelity | The claim MUST be representable without platform calculation, prediction, recommendation, strategy, or discretionary interpretation. |
| Ownership preservation | The claim MUST remain evidence when it touches identity, accounting, lifecycle, authorization, execution, or judgment owned elsewhere. |
| Provider neutrality | The observation kind MUST be definable without a vendor name, product capability, transport, SDK, or provider field. |
| Correction safety | A later correction, revision, or retraction MUST be representable without changing the meaning of the earlier Observation Event. |

Failure of any test places that output outside the Observation domain. A future source specification MUST classify mixed outputs individually and MUST NOT admit a source wholesale by reputation, vendor category, or delivery mechanism.

## 6. Source Classification Matrix

The following categories are eligible Observation Source categories within the limits stated. Eligibility does not constitute M39 v1 support.

| Source category | Qualifying externally observable facts | Why it belongs to Observation | Constitutional limit |
| --- | --- | --- | --- |
| Exchange market data | Trades, quotes, auction results, market states, venue statistics, and published calendars | These are direct external statements about market activity or state | A market report is not a platform order, execution decision, or transaction |
| Market price feeds | Attributed current or historical price, valuation, NAV, rate, or benchmark observations | They relay externally observable valuation evidence | The feed does not establish asset identity, executability, portfolio value, or accounting truth |
| Corporate disclosures | The existence, issue time, declared terms, and attributed contents of issuer publications | Publication and issuer-declared content are externally observable evidence | Disclosure content does not become Registry adjudication, ledger truth, or platform analysis merely by being observed |
| Earnings releases | Issuer-reported results, periods, release events, and explicitly stated measures | The issuer’s publication is an attributable external event | Growth, quality, surprise, valuation, and investment conclusions derived by the platform are excluded |
| Dividends | Declared, changed, cancelled, ex-date, record-date, and payment-date claims where supplied with explicit semantics | Distribution announcements and status changes are observable corporate-event evidence | Registry owns any lifecycle adjudication; Ledger & Accounting owns recorded cash events; Observation performs neither |
| Splits | Announced or effective split terms and source-reported status | A split announcement or effective event is external structural-event evidence | Asset Foundation adjudicates canonical structural consequences and identity relationships |
| Regulatory announcements | Filings, notices, decisions, enforcement publications, and their attributed issue or effective times | Publication by an external authority is observable evidence | Observation does not decide legal meaning, platform authorization, compliance status, or action |
| Macroeconomic publications | Officially published measurements, revisions, release times, and declared periods | They are external measurements of economic conditions | Forecasts, scenario analysis, inferred regimes, and investment conclusions are excluded |
| Analyst publications | Publication existence, authorship, issue time, covered subject, and attributable source statements | The act and content of publication are externally observable | Predictions, recommendations, consensus, and Investment Judgment remain outside Observation semantics |
| News providers | Attributed reports, publication events, corrections, retractions, and news references | A published report is external event evidence with provenance | Observation does not infer importance, truth, sentiment, causality, or an investment action |
| Sentiment providers | Attributed source-reported sentiment measurements, classifications, or publication events | The fact that an external source published a qualified measurement is observable | Observation does not calculate sentiment, endorse it as judgment, or convert it into a recommendation or strategy |
| Alternative data sources | Attributed externally measured activity, usage, traffic, weather, geospatial, supply-chain, or other real-world signals | These sources witness external conditions not represented by conventional market feeds | Platform-derived features, scores, predictions, and conclusions remain Analytics or Decision Intelligence concerns |
| Future observation classes | A new class satisfying every rule in §5 and §13 | The boundary is based on fact semantics rather than a closed provider list | A new class requires its own governed canonical semantics and cannot reinterpret an existing class |

Source category membership is not authority. A qualifying source remains a witness, and every claim retains its provenance and qualification.

## 7. Explicit Exclusions

The following concepts are outside the Observation domain. Their use of, response to, or presentation of an Observation does not make them Observation Sources.

| Excluded concept | Boundary reason |
| --- | --- |
| Trading | Trading chooses or performs an action; Observation only represents external evidence |
| Execution | Execution evaluates or carries out an instruction; Observation grants no executability or authority |
| Portfolio | Portfolio state and portfolio meaning are owned outside Market Observation |
| Transactions | Transactions are Ledger & Accounting facts and MUST NOT be created, amended, or authorized by Observation |
| Orders | Platform order intent, lifecycle, routing, admission, and fulfillment are action-domain concepts |
| Watchlists | Watchlist membership is Experience-owned interaction state, not an external fact source |
| Alerts | Alert definitions, trigger evaluation, notification state, and delivery are response or Experience concerns |
| Screeners | Screening filters, ranks, or selects candidates from facts; it does not originate external facts |
| Calculations | Arithmetic or transformation performed by the platform is a derivation, not an Observation Event |
| Derived indicators | A derived indicator as platform analytical meaning is excluded. Observation MAY record only the externally observable fact that an origin published a stated measurement; it does not own, reproduce, endorse, or adopt the indicator’s analytical semantics |
| Predictions | Statements about an uncertain future are judgment, not observed external state |
| Recommendations | Advice about what to do is Investment Judgment or Decision Intelligence, not Observation |
| Strategies | Policies for choosing actions belong to decision or portfolio concerns |
| Provider SDK behavior | SDK types, defaults, retries, exceptions, and lifecycle are implementation details |
| Transport protocols | HTTP, REST, WebSocket, GraphQL, CSV, files, and equivalent mechanisms carry data but do not define its meaning |
| Caching | Cache presence, expiry, invalidation, and retrieval are operational concerns; a cache is not an Observation Origin |
| Storage implementation | Tables, documents, objects, databases, and retention mechanisms do not own observation semantics |
| Authentication | Proving an actor or service identity does not create or interpret an Observation Event |
| Authorization | Permission and authority decisions remain with the existing non-domain authentication, authorization, approval, and human-owned authority boundaries; Observation supplies no authority |
| Scheduling | Deciding when work occurs is operational coordination, not an external fact |
| Runtime orchestration | Invocation, sequencing, retries, failover, and process topology are runtime responsibilities |

An excluded mechanism MAY carry or consume an Observation without entering the Observation domain. An excluded domain MAY reference an Observation without acquiring ownership of it.

## 8. Boundary Rules

The following rules are immutable within this specification:

1. Observation MUST represent externally observable facts or source-reported claims only.
2. Observation MUST NOT perform calculations.
3. Observation MUST NOT compute derived indicators.
4. Observation MUST NOT own derived analytics.
5. Observation MUST NOT predict future state.
6. Observation MUST NOT recommend an action.
7. Observation MUST NOT define or execute a strategy.
8. Observation MUST NOT perform trading or execution.
9. Observation MUST NOT create, admit, amend, or interpret a transaction or order.
10. Observation MUST NOT evaluate a portfolio or own portfolio-derived meaning.
11. Observation MUST NOT own identity, classification adjudication, or lifecycle adjudication.
12. Observation MUST NOT own authorization, authentication, scheduling, or runtime control.
13. Observation MUST NOT own provider behavior, transport, cache, or storage implementation.
14. Observation MUST preserve external-source uncertainty and MUST NOT manufacture missing facts.
15. Observation MUST preserve the distinction between a source claim and the platform’s acceptance, interpretation, or use of that claim.
16. Observation MAY be consumed by Analytics, Decision Intelligence, Portfolio Intelligence, Trust & Evaluation, Experience, or future AI modules, but consumption SHALL NOT transfer semantic ownership.

Representation-preserving canonical normalization remains governed by the existing provider boundary. It is not a calculation owned by Observation and MUST NOT aggregate, smooth, score, forecast, infer, or change the meaning of the source claim.

## 9. Provider and Mechanism Independence

Observation Source semantics SHALL NOT depend on any concrete provider, vendor, service, product, library, protocol, format, or infrastructure component.

In particular, Observation Source MUST NOT depend on:

- Yahoo;
- Polygon;
- AlphaVantage;
- IEX;
- SEC;
- TradingView;
- Finnhub;
- Supabase;
- Redis;
- HTTP;
- REST;
- WebSocket;
- GraphQL;
- CSV;
- files;
- databases; or
- any equivalent present or future implementation choice.

These names identify possible witnesses, relays, authorities, transports, formats, or infrastructure. None is part of the canonical Observation vocabulary.

A concrete source identity MAY appear only as provenance. Consumers MUST NOT branch on that identity to determine the meaning of an Observation Event. Source quality or availability MAY be evaluated by its existing constitutional owner, but such evaluation MUST NOT redefine the observation itself.

Replacing, adding, or removing a provider MUST NOT require a change to existing Observation Event or Observation Payload semantics. Losing any single provider MUST remain an operational event, never an architectural event.

## 10. Ownership Matrix

Every concept has exactly one semantic owner. Reference, relay, storage, presentation, or consumption does not create shared ownership.

| Concept or boundary | Canonical owner | Relationship to Observation |
| --- | --- | --- |
| Observation Source classification | Market Intelligence | Defines which external witness outputs qualify as Market Observation evidence |
| Observation Event, Payload, Timestamp, and Origin semantics | Market Intelligence | Sole semantic ownership under this specification |
| External source claim | Observation Origin | The external origin authors the claim; it does not own the platform’s canonical Observation semantics or any downstream verdict |
| Catalog | Asset Foundation through the Registry’s catalog | Observation may reference catalog identities but cannot add, merge, classify, or adjudicate them |
| Universe search-scope semantics | Frozen M37 Universal Asset Search Boundary | External-universe candidates retain witness provenance and remain discovery evidence, not Market Observations or canonical identity |
| Asset Registry | Asset Foundation | Owns `asset_id`, existence, identifiers, classification, lifecycle, and adjudication; receives Observation evidence only where already governed |
| Execution Intent | Existing frozen execution-intent boundary | MAY consume evidence but cannot be created, approved, or authorized by Observation |
| Portfolio | Portfolio Intelligence, with Ledger & Accounting retaining source facts | MAY consume observations for owned derivations; Observation owns no holdings, valuation result, allocation, performance, or risk |
| Connectivity & Ingestion | Connectivity & Ingestion | Owns capture, canonical event proposals, provenance at capture, review, and reconciliation when external facts enter the path toward ledger truth; it shares the witness-never-authority contract with Market Intelligence but does not own Observation semantics |
| Authorization | Existing non-domain authentication, authorization, approval, and human-owned authority boundaries | Retain their frozen facts, gates, and decision authority under Law 12; Observation supplies no authentication fact, permission, approval, delegation, or authority |
| Runtime | Existing runtime and operational owners | Invokes or coordinates capabilities without owning Observation semantics |
| Provider Layer | Existing Market Data provider boundary | Owns source-specific translation and witness interaction; does not own canonical Observation meaning |
| Storage | Existing persistence and infrastructure owners | Preserves representations without becoming source, origin, or semantic owner |
| Analytics | The constitutional domain owning each derived result | Consumes observations and owns its calculations; derived results do not become Observations |
| Future AI modules | Existing Decision Intelligence, Trust & Evaluation, Wealth Intelligence, or Experience owners according to output meaning | MAY consume observations; MUST NOT claim source authority, mutate observations, or reclassify judgments as facts |
| Experience composition | Experience Platform | MAY render and compose observations; MUST NOT derive or reinterpret source meaning |

No row grants new authority. Where a prior milestone owns a concept, that prior ownership remains authoritative.

## 11. Boundary Matrix

| Boundary question | Inside Observation | Outside Observation | Required resolution |
| --- | --- | --- | --- |
| What happened or was reported externally? | Attributed external fact or source claim | Platform interpretation of why it matters | Preserve the fact in Observation; send interpretation to its owning analytical or decision domain |
| Is this observation evidence or a fact entering the truth path? | Observation evidence remains Market Intelligence-owned testimony | Fact capture, canonical event proposals, review, and reconciliation toward ledger truth belong to Connectivity & Ingestion | Apply the shared witness-never-authority contract: Market Intelligence owns observation evidence; Connectivity & Ingestion owns external-fact ingestion; neither witness becomes authority |
| What is the subject? | Reference to an already-governed identity or explicitly scoped external subject claim | Identity minting, merging, or adjudication | Asset Foundation retains identity authority |
| What time does the claim mean? | Source-established observation, occurrence, effective, or publication time | Retrieval, cache, schedule, display, or local-clock substitution | Preserve temporal semantics and keep operational times separate |
| What did a source publish? | Publication event and attributed source content within the eligible fact subset | Adoption of predictions, recommendations, or strategy as Observation meaning | Retain publication evidence; judgment remains outside Observation |
| What value did an external methodology report? | Attributed source-reported measurement with disclosed qualification | Recalculation, endorsement, aggregation, or platform-derived score | Represent the external claim only |
| Is the claim correct or trustworthy? | Source qualification and provenance carried with the claim | Independent scoring, evaluation, adjudication, or correction | Trust & Evaluation, validation, or another frozen owner assesses it without rewriting the event |
| What should the user do? | Nothing | Prediction, recommendation, intent, strategy, order, or execution | Decision and action domains retain ownership |
| What does this mean for a portfolio? | Nothing | Valuation result, return, allocation, risk, exposure, or performance | Portfolio Intelligence performs and owns the derivation |
| How did the data arrive? | Provenance may identify origin and relay | SDK, protocol, endpoint, file, retry, cache, and storage behavior | Implementation remains outside the semantic boundary |
| How is a correction handled? | A new attributed Observation Event | Mutation or silent replacement of the earlier event’s meaning | Preserve both meanings and explicit lineage under a future governed event contract |

## 12. Immutability, Provenance, and Reproducibility

### 12.1 Immutability

An Observation Event MUST be immutable in meaning. Later arrival, correction, validation, storage, or presentation SHALL NOT retroactively alter what the source was represented as having reported.

Immutability applies to the canonical event meaning and does not prescribe a database, append-only log, object model, or retention mechanism.

### 12.2 Provenance

Every Observation Event MUST preserve enough semantic provenance to distinguish:

- the Observation Origin;
- any materially relevant relay role;
- the source-established temporal meaning; and
- explicit uncertainty, qualification, correction, or retraction status.

Provenance MUST NOT be used as a substitute for canonical semantics. Provider identity alone does not establish fact kind, quality, identity, freshness, or authority.

### 12.3 Reproducibility

The meaning of a canonical Observation Event MUST be reproducible from its canonical content and governed vocabulary without consulting:

- a live provider;
- current provider documentation;
- provider-specific code;
- a transport session;
- mutable runtime state;
- a cache; or
- a current analytical model.

Reproducibility of meaning does not require WP2 to define persistence or historical replay. It requires that provider replacement, runtime change, or later analysis cannot reinterpret an already represented event.

## 13. Extensibility Rules

A future observation class MAY be added only when it satisfies all of the following:

1. It passes every qualification in §5.
2. Its semantics describe an external fact or source-reported claim without naming a provider.
3. Its canonical meaning is distinct from every existing observation class.
4. It identifies its Observation Origin and temporal semantics.
5. It defines how absence, uncertainty, correction, revision, and retraction preserve source meaning.
6. It preserves all existing ownership boundaries.
7. It introduces no calculation, prediction, recommendation, strategy, portfolio meaning, or execution authority.
8. It can coexist with existing classes without changing their fields, meanings, availability, or conformance rules.
9. It does not require existing consumers to understand the new class in order to preserve their current behavior.
10. It receives separately approved authority before implementation or public exposure.

Future observation types MUST be additive. A new type MUST NOT:

- reinterpret an existing type;
- add provider-specific assumptions to the core model;
- make a concrete provider mandatory;
- widen M39-WP1 implicitly;
- alter the M38 reserved contribution;
- turn provenance into semantic branching;
- convert source testimony into identity, ledger, analytical, or decision authority; or
- require changes to frozen consumers merely to remain conformant.

A new provider for an existing observation class requires no semantic extension when it can produce the existing canonical meaning. A new source output that cannot be represented without changing an existing class requires a separately governed new class; it MUST NOT be forced into the nearest existing shape.

## 14. Constitutional Rules

The following invariants are normative and cumulative.

### Provider neutrality

- **OS-01:** Observation semantics MUST be provider-neutral.
- **OS-02:** Provider names, SDK concepts, field names, transport behavior, and infrastructure choices MUST NOT enter canonical Observation vocabulary.
- **OS-03:** A provider identity MAY be retained as provenance but MUST NOT control semantic interpretation.

### Immutability and fact representation

- **OS-04:** An Observation Event MUST represent exactly one attributable external fact or source-reported claim at its governed semantic granularity.
- **OS-05:** An Observation Event MUST be immutable in meaning.
- **OS-06:** Corrections, revisions, retractions, and later measurements MUST be represented without rewriting earlier event meaning.
- **OS-07:** Missing, unknown, disputed, or qualified evidence MUST remain explicit and MUST NOT be fabricated or defaulted.
- **OS-08:** Observation MUST remain evidence and MUST NOT assert identity, accounting truth, judgment, or authority.

### Reproducibility and temporal integrity

- **OS-09:** Canonical Observation meaning MUST be reproducible without a live provider or current runtime state.
- **OS-10:** Observation Timestamp meaning MUST be explicit and MUST NOT be replaced by retrieval, receipt, cache, schedule, or display time.
- **OS-11:** Distinct temporal facts MUST NOT be collapsed into an ambiguous timestamp.

### Deterministic ownership and separation of concerns

- **OS-12:** Market Intelligence MUST remain the sole semantic owner of Market Observation.
- **OS-13:** Every referenced identity, ledger fact, portfolio result, judgment, authorization fact, and presentation state MUST retain its existing constitutional owner.
- **OS-14:** Observation MUST NOT calculate, analyze, predict, recommend, strategize, authorize, trade, execute, or mutate adjacent-domain state.
- **OS-15:** Consumers MAY reference Observation evidence but MUST NOT redefine, overwrite, or acquire ownership of it.
- **OS-16:** Transport, storage, cache, provider, and runtime layers MUST NOT acquire semantic ownership through custody or invocation.

### Forward compatibility and single responsibility

- **OS-17:** New observation classes MUST be additive and MUST preserve existing semantics unchanged.
- **OS-18:** A source with mixed outputs MUST expose only its qualifying fact-bearing subset to Observation semantics.
- **OS-19:** Every observation class MUST have one responsibility: representing one governed kind of external fact or source claim.
- **OS-20:** A new provider for an existing class MUST be an implementation event, not an architectural event.
- **OS-21:** A future class MUST NOT be admitted through a provider-private extension.
- **OS-22:** This source boundary MUST NOT leak implementation, runtime, API, transport, or storage assumptions into future observation contracts.

## 15. Constraints

M39-WP2 SHALL NOT:

- define an API, endpoint, request, response, or serialization format;
- define a provider interface, adapter, capability declaration, or integration sequence;
- select, rank, route, fail over, or configure providers;
- define network, file, database, message, or streaming transport;
- define caching, persistence, retention, indexing, or schema behavior;
- define authentication, authorization, tenancy, or permission behavior;
- define scheduling, jobs, retries, concurrency, or runtime orchestration;
- define calculation, analytics, scoring, prediction, recommendation, or strategy behavior;
- define frontend, Experience, alert, watchlist, or screener behavior;
- define execution, order, transaction, portfolio, or ledger behavior;
- bind or activate an M38 contribution;
- modify the M39-WP1 `MarketObservation` contract or public boundary;
- authorize any included source category for M39 v1; or
- amend any frozen milestone.

No example, category, or extension rule in this document SHALL be interpreted as implementation authorization.

## 16. Architectural Examples — Informative

This section is non-normative. It illustrates application of the normative rules above.

### 16.1 Valid Observation Sources

- A venue publishes an official closing-auction price with the auction time and currency. The publication reports an external market fact.
- An issuer publishes a dividend declaration with explicitly labeled declaration, ex, record, and payment dates. The declaration is observable evidence; its downstream accounting consequences remain elsewhere.
- A regulator publishes a filing at an attributable time. The filing event is observable even though legal interpretation is outside Observation.
- A statistical authority releases a revised inflation value for a declared period. The original release and revision are separate attributable events.
- A news publisher issues and later corrects an attributed report. Both the publication and correction can be represented without treating either as investment advice.
- An external sentiment source publishes a methodology-qualified score. The fact that the source reported that score can be observed; the platform does not reproduce or endorse the calculation.
- An alternative-data source reports an externally measured activity count for a stated interval. The measurement can be represented without deriving an investment conclusion.

### 16.2 Invalid Observation Sources

- A portfolio return calculator, because it derives a result from ledger and observation inputs.
- A technical-indicator function computing RSI from price history, because it performs a platform calculation.
- A screener ranking assets by momentum, because it calculates and selects.
- An AI model predicting next month’s price, because it produces judgment about the future.
- A recommendation engine proposing a purchase, because it advises action.
- A watchlist, because it records Experience interaction state.
- An alert trigger, because it evaluates a condition and initiates a response.
- An order manager, because it owns action lifecycle rather than external fact testimony.
- A cache or database, because custody does not make infrastructure an Observation Origin.
- An HTTP client or provider SDK, because delivery behavior has no observation semantics.

### 16.3 Ambiguous Cases and Resolution

| Ambiguous case | Resolution |
| --- | --- |
| A market trade print versus a user trade | The externally reported trade print may be an Observation; the user’s trade instruction, execution, and Transaction are excluded |
| A split announcement versus canonical lifecycle state | The announcement is Observation evidence; Asset Foundation adjudicates the structural event and identity consequences |
| An earnings release versus an earnings-growth value | The released figures are source claims; growth calculated by the platform is Analytics |
| An analyst report versus its recommendation | Publication metadata and attributable source statements may be observed; the recommendation and predicted outcome are Investment Judgment, not Observation semantics |
| A news article versus inferred sentiment | The article and publication event may be observed; sentiment inferred by the platform is a derived analytical result |
| A source-published indicator versus a platform-derived indicator | The source’s publication may be represented as an attributed external claim; recomputation, endorsement, or use as canonical platform analysis is outside Observation |
| A macro release calendar versus a scheduler | The externally published release time may be observed; deciding when platform work runs is Scheduling and is excluded |
| A cached observation versus a source | The underlying external origin remains the source; cache status is provenance or operational context and the cache is never the origin |
| A regulatory notice versus an authorization decision | The notice is external evidence; whether an actor or operation is authorized remains with the authorization owner |
| An order-book snapshot versus a platform Order | External market-depth state may be an Observation; a platform Order and its lifecycle remain excluded |

## 17. Future Extension Guidance

A proposal for a future observation class SHOULD answer, without implementation detail:

1. What externally observable fact or source-reported claim does the class represent?
2. Why is that meaning not already covered by an existing class?
3. Who or what is the Observation Origin?
4. What does each material timestamp mean?
5. Which content is direct source evidence, and which adjacent content is excluded derivation or judgment?
6. How are absence, uncertainty, revision, correction, and retraction represented semantically?
7. Which existing constitutional owners are referenced without transfer of ownership?
8. Can multiple independent providers supply the same canonical meaning?
9. Can consumers that do not understand the new class retain their existing behavior unchanged?
10. Does the proposal remain compatible with M38 and M39-WP1?

A proposal that cannot answer all ten questions without naming an implementation mechanism is not ready for architectural admission.

Extension review MUST classify the proposed semantics before any provider or transport is selected. Provider availability SHALL NOT justify weakening the canonical model or importing provider-private vocabulary.

## 18. Conformance and Independent Review

A future Market Observation source or source-class specification conforms to M39-WP2 only when objective review establishes all of the following:

| Identifier | Required proof |
| --- | --- |
| SRC-01 | Every admitted output passes the complete §5 qualification test |
| SRC-02 | Mixed-content sources exclude calculations, judgments, recommendations, strategies, and actions |
| SRC-03 | Observation Origin and temporal meaning are attributable without provider-specific semantics |
| SRC-04 | The source contract contains no provider, SDK, transport, storage, cache, authentication, authorization, scheduling, or runtime dependency |
| BND-01 | Every explicit exclusion in §7 remains outside Observation |
| BND-02 | Every boundary case preserves the owner identified in §§10–11 |
| BND-03 | Observation performs no calculation, analysis, prediction, recommendation, strategy, trading, execution, or mutation |
| OWN-01 | Market Intelligence remains the sole semantic owner of Market Observation |
| OWN-02 | Asset Foundation retains identity and Registry adjudication |
| OWN-03 | Connectivity & Ingestion, Ledger, Portfolio, Decision, the non-domain authentication and authorization boundaries, Runtime, Provider, Storage, Analytics, AI, and Experience retain their existing authority |
| INV-01 | Event meaning is immutable and corrections do not rewrite earlier meaning |
| INV-02 | Meaning is reproducible without a live provider or mutable runtime state |
| EXT-01 | New observation classes are additive and preserve all existing semantics |
| EXT-02 | No provider-private extension enters canonical vocabulary |
| CMP-01 | M38 contracts remain unchanged |
| CMP-02 | M39-WP1 contracts, availability, derivation, ownership, feature expectations, and public boundary remain unchanged |
| SCP-01 | The proposal grants no implicit implementation or runtime authority |

The independent reviewer SHALL verify:

- constitutional consistency;
- absence of provider leakage;
- absence of runtime assumptions;
- absence of transport assumptions;
- deterministic ownership boundaries;
- complete treatment of excluded concepts;
- additive future extensibility;
- deterministic terminology; and
- compatibility with M38 and M39-WP1.

Conformance to this specification establishes source-boundary eligibility only. It does not approve implementation, provider integration, runtime adoption, storage, an API, or public exposure.

## 19. Canonical Closure

M39-WP2 defines the constitutional source boundary for future Market Observation work.

After ratification:

- future source specifications MUST conform to this document;
- included categories remain eligibility classifications rather than implementation commitments;
- excluded concepts remain outside Observation unless prior constitutional governance is explicitly amended;
- provider and mechanism changes remain invisible to canonical observation semantics; and
- M38 and M39-WP1 remain authoritative and unchanged.

Nothing in this specification reopens a completed milestone or authorizes implementation.
