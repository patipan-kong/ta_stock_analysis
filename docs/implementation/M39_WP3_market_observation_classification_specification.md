# M39-WP3 — Market Observation Classification Specification

**Status:** Canonical specification candidate for independent constitutional review

**Authority:** M39-WP3

**Nature:** Normative constitutional classification specification

## 1. Purpose

This specification defines the canonical classification system for Market Observation.

Observation Classification identifies the semantic kind of fact represented by an Observation Event. It enables a qualifying event to retain the same meaning regardless of which Observation Source witnessed it or which provider, runtime, transport, storage system, API, or implementation later carries it.

Classification is a statement about the represented fact. It is not:

- a provider capability;
- a source category;
- a transport or storage discriminator;
- an implementation dispatch instruction;
- a runtime status;
- an analytical label;
- an asset classification;
- an availability outcome; or
- authority to act.

This specification establishes constitutional classifications only. It does not authorize implementation, provider integration, runtime adoption, persistence, public exposure, or amendment of an existing contract.

## 2. Authority and Compatibility

This specification is subordinate to the Platform Architecture and preserves all ratified governance through M39-WP2.

In particular:

- M38 remains complete and frozen;
- the M38 reserved market contribution and all M38 envelope, attachment, composition, availability, and ownership contracts remain unchanged;
- M39-WP1 remains complete and frozen;
- the M39-WP1 `MarketObservation` contract, public boundary, availability model, exact provider derivation, feature expectations, and execution separation remain unchanged;
- M39-WP2 remains authoritative for Observation Source eligibility, Observation Event semantics, source boundaries, exclusions, and provider independence;
- Market Intelligence remains the sole semantic owner of Market Observation and Observation Classification;
- Asset Foundation remains the sole owner of canonical asset identity and Registry adjudication;
- Connectivity & Ingestion retains ownership of external-fact ingestion toward ledger truth;
- all existing ledger, portfolio, decision, authorization, execution, provider, runtime, storage, analytics, Trust, and Experience boundaries remain unchanged; and
- Observation remains evidence, never identity authority, ledger truth, investment judgment, execution authority, or presentation authority.

The classes defined here are constitutionally admissible semantic categories. Their definition SHALL NOT imply current support, provider capability, runtime enablement, public exposure, persistence, or admission into the M39-WP1 `MarketObservation` contract.

## 3. Scope

M39-WP3 defines:

- canonical Observation Classification vocabulary;
- principles governing classification;
- the closed initial set of canonical Observation Classes;
- the semantic boundary, ownership, examples, and exclusions of each class;
- deterministic single-class assignment;
- treatment of mixed-content and ambiguous candidates;
- the relationship between source eligibility and event classification;
- additive admission rules for future classes;
- constitutional invariants; and
- objective conformance criteria.

M39-WP3 does not define:

- an API, endpoint, request, response, or serialization;
- a provider interface, adapter, capability, or integration;
- runtime dispatch, scheduling, orchestration, retry, or failover;
- transport, storage, caching, indexing, retention, or schema;
- authentication, authorization, tenancy, or permissions;
- analytics, calculations, predictions, recommendations, or strategies;
- execution, orders, transactions, portfolios, or ledger behavior;
- user-interface labels or composition behavior; or
- implementation of any canonical class.

## 4. Canonical Vocabulary

### 4.1 Observation Classification

**Observation Classification** is the Market Intelligence-owned determination of what governed kind of External Fact or Source-Reported Claim one Observation Event represents.

Classification MUST be determined from canonical fact meaning at the event’s governed semantic granularity. It MUST NOT be determined from provider identity, source product, transport, storage location, endpoint, SDK type, field name, or runtime path.

Observation Classification is distinct from Asset Classification, identity adjudication, and lifecycle adjudication. It does not amend M39-WP2’s prohibition against Observation owning those Asset Foundation concerns.

### 4.2 Canonical Observation Class

A **Canonical Observation Class** is a provider-neutral, mutually exclusive semantic category whose boundary defines one governed kind of fact that an Observation Event may represent.

Every admitted Observation Event MUST belong to exactly one Canonical Observation Class. A class name is constitutional vocabulary; this specification does not prescribe how that name is encoded, serialized, persisted, or transported.

### 4.3 Class Boundary

A **Class Boundary** is the normative distinction between facts admitted to one Canonical Observation Class and facts owned by another class or excluded from Observation.

A Class Boundary is defined by represented meaning. Similar source, subject, timestamp, document, or delivery mechanism does not erase that boundary.

### 4.4 Classifying Fact

The **Classifying Fact** is the single External Fact or Source-Reported Claim whose meaning determines an Observation Event’s class.

Context, provenance, qualifications, and related claims MAY accompany the Classifying Fact only where permitted by prior governance. They MUST NOT cause the event to acquire another class.

### 4.5 Publication Event and Published Content

A **Publication Event** is the externally observable fact that material was issued, released, corrected, revised, or retracted.

**Published Content** consists of claims contained in that material. A publication event and each independently qualifying content claim are distinct possible facts. They MUST NOT be collapsed when they require different classes.

Classification of a publication does not endorse its contents, make those contents true, or transfer analytical or decision ownership to Observation.

### 4.6 Classification Ambiguity

**Classification Ambiguity** exists when the Classifying Fact is insufficiently bounded to determine exactly one Canonical Observation Class.

Ambiguity is a failure to establish canonical meaning. It MUST NOT be resolved by provider-specific precedence, source reputation, implementation convenience, a catch-all default, or silent multi-class assignment.

### 4.7 Source Category

A **Source Category** is the M39-WP2 classification of the kind of external witness from which eligible fact-bearing output may originate.

Source Category and Observation Classification are independent:

- Source Category answers, “What kind of source can witness the claim?”
- Observation Origin answers, “Who or what is responsible for the claim?”
- Observation Classification answers, “What kind of fact does this event represent?”

No answer determines either of the others.

## 5. Classification Principles

### 5.1 Semantic-first

Classification MUST follow the canonical meaning of the Classifying Fact. Names used by a source, provider, file, endpoint, feed, or SDK are evidence only and SHALL NOT be canonical authority.

### 5.2 Provider-neutral

The same fact meaning MUST receive the same classification when witnessed by different qualifying sources. Replacing, adding, or removing a provider MUST NOT change class semantics.

### 5.3 Deterministic

Given the same canonical fact meaning and the same ratified classification vocabulary, independent conforming reviews MUST reach the same class.

### 5.4 Exactly one class

Every admitted Observation Event MUST have exactly one Canonical Observation Class. Classes MUST NOT overlap at assignable semantic granularity.

### 5.5 Single responsibility

One Observation Event represents one governed fact kind. An event MUST NOT act as a container for unrelated fact kinds merely because they appeared in one external document, response, publication, or message.

### 5.6 Additive evolution

Future classes MUST be introduced additively. A new class MUST NOT reinterpret, narrow, widen, rename, alias, or supersede an existing class.

### 5.7 Forward compatibility

An existing class and an event already classified under it MUST retain their meaning after new classes are admitted. Existing consumers MUST NOT be required to understand a future class to preserve their current behavior.

### 5.8 Evidence, never authority

Classification states what kind of evidence is represented. It does not state that the evidence is correct, trusted, canonical identity, ledger truth, analytically significant, suitable for a portfolio, or actionable.

## 6. Canonical Observation Classes

The following table defines the closed initial class set. No unlisted class exists without the separate admission required by §10.

| Canonical class | Classifying meaning | Semantic boundary | Owner |
| --- | --- | --- | --- |
| Market Price | An externally observed or reported market value, quote component, valuation mark, rate, NAV, or equivalent worth observation | Value evidence only; no portfolio valuation, execution eligibility, return, forecast, or transaction meaning | Market Intelligence |
| Dividend Event | An external declaration or source-reported status of a dividend or distribution and its explicit terms or dates | Distribution-event evidence only; no cash transaction, holding entitlement, tax result, or lifecycle adjudication | Market Intelligence |
| Split Event | An external announcement or source-reported status of a split and its explicit terms or dates | Split-event evidence only; no identity mutation, quantity rewrite, ledger event, or canonical lifecycle adjudication | Market Intelligence |
| Corporate Action | An external declaration or source-reported status of a corporate action other than a dividend or split | Other corporate-action evidence only; Dividend Event and Split Event are expressly excluded | Market Intelligence |
| Corporate Disclosure | An issuer-attributed publication or disclosed corporate fact that is not an Earnings Publication and whose Classifying Fact is not a Dividend Event, Split Event, or other Corporate Action | Issuer disclosure evidence only; no Registry adjudication, accounting truth, legal conclusion, or platform analysis | Market Intelligence |
| Earnings Publication | An issuer-attributed publication of financial-period results or explicitly reported earnings measures | Earnings-publication evidence only; no computed growth, surprise, quality, valuation, forecast, or investment conclusion | Market Intelligence |
| Regulatory Publication | An externally observable filing, notice, decision, rule, enforcement publication, or equivalent publication made in a regulatory function | Regulatory publication evidence only; no legal interpretation, compliance decision, authorization, or action | Market Intelligence |
| Market Status | An externally reported state of a market, venue, instrument session, auction, halt, suspension, or published market calendar | Market-state evidence only; no scheduling control, execution permission, market prediction, or strategy | Market Intelligence |
| Macroeconomic Publication | An externally published macroeconomic measurement, revision, release, or declared reference period | Published macro evidence only; no forecast, inferred regime, scenario, or investment conclusion | Market Intelligence |
| News Publication | An externally observable journalistic or news publication event and its attributable eligible fact-bearing report | News evidence only; no inferred truth, importance, causality, sentiment, prediction, recommendation, or strategy | Market Intelligence |
| Analyst Publication | An externally observable analyst publication event and its attributable eligible fact-bearing statements | Publication evidence only; no adoption of analysis, consensus, target, prediction, recommendation, or judgment | Market Intelligence |
| Sentiment Publication | An externally published, attributable sentiment measurement or classification | Source-reported sentiment evidence only; no platform sentiment calculation, endorsement, prediction, recommendation, or strategy | Market Intelligence |
| Alternative Data Observation | An externally measured real-world condition not governed by another existing class | Direct external measurement evidence only; no platform-derived feature, score, inference, prediction, or conclusion | Market Intelligence |

### 6.1 Market Price

**Meaning.** Market Price represents an attributable external observation of worth or a source-reported market value at an explicit semantic time.

**Boundary.** The class includes the observed value and necessary qualifications. A reported bid, ask, last value, official close, NAV, appraisal, benchmark value, or rate MAY qualify when its price meaning remains explicit and provider-neutral.

**Examples.**

- a source-reported last traded price;
- an official closing value;
- a published fund NAV; and
- an attributed bid or ask observation that carries no execution guarantee.

**Exclusions.**

- an executable quote or execution-evidence contract;
- a portfolio valuation;
- a calculated return;
- an internally estimated fair value;
- a predicted price;
- a target price or recommendation; and
- an accounting transaction.

The M39-WP1 `MarketObservation` is constitutionally within Market Price meaning. This statement does not add a field, change its shape, widen its public boundary, or alter its availability, provider derivation, normalization, feature, or execution-separation rules.

The M39-WP1 `price_kind` remains the canonical normalized meaning of a price within that frozen contract. It is not redefined as an Observation Classification field and MUST NOT be conflated with the class system established here.

### 6.2 Dividend Event

**Meaning.** Dividend Event represents an external declaration, change, cancellation, or source-reported status concerning a dividend or distribution.

**Boundary.** Declared amount, unit, currency, ex-date, record date, payment date, status, and equivalent source-stated terms MAY belong when their distinct temporal meanings remain explicit.

**Examples.**

- an issuer declares a cash dividend;
- a declared dividend is cancelled; and
- a source publishes a corrected ex-date.

**Exclusions.**

- a cash receipt or transaction;
- an entitlement calculated from holdings;
- withholding or tax treatment;
- portfolio income;
- Registry lifecycle adjudication; and
- a prediction of a future dividend.

### 6.3 Split Event

**Meaning.** Split Event represents an external announcement, correction, effective status, or source-reported terms of an instrument split or reverse split.

**Boundary.** The event may preserve explicitly reported ratio, announcement time, effective time, and status. It does not adjudicate the canonical consequences of those terms.

**Examples.**

- an issuer announces a two-for-one split;
- a venue reports a split effective; and
- a source corrects a previously reported ratio.

**Exclusions.**

- minting, merging, replacing, or relating asset identities;
- rewriting historical holdings;
- calculating adjusted prices;
- recording a ledger event; and
- applying the split to a portfolio.

### 6.4 Corporate Action

**Meaning.** Corporate Action represents an external declaration or source-reported status of an issuer action affecting instruments, rights, obligations, or capital structure, where that action is neither a dividend nor a split.

**Boundary.** This class is assignable only to the action terms or status themselves. Dividend and split semantics are disjoint and MUST use their dedicated classes.

**Examples.**

- an announced tender offer;
- a rights offering;
- a redemption notice; and
- an announced merger term, without identity adjudication.

**Exclusions.**

- Dividend Event;
- Split Event;
- Registry identity or lifecycle adjudication;
- ledger proposals or recorded transactions;
- holder eligibility calculations;
- legal conclusions; and
- portfolio consequences.

### 6.5 Corporate Disclosure

**Meaning.** Corporate Disclosure represents an issuer-attributed publication event or issuer-disclosed corporate fact outside the more specific Earnings Publication, Dividend Event, Split Event, and Corporate Action boundaries.

**Boundary.** The class preserves the fact and attributable eligible content of issuer disclosure. It does not convert disclosure into platform truth or analysis.

**Examples.**

- an issuer publishes a governance update;
- an issuer releases an operational update; and
- an issuer corrects a previously published non-earnings disclosure.

**Exclusions.**

- financial-period results governed by Earnings Publication;
- dividend, split, or other action terms governed by their dedicated classes;
- Registry classification or identity conclusions;
- accounting admission;
- legal interpretation; and
- platform-derived significance.

### 6.6 Regulatory Publication

**Meaning.** Regulatory Publication represents an external publication made in a regulatory, supervisory, rulemaking, filing-receipt, or enforcement function.

**Boundary.** Classification follows the represented regulatory publication function, not a provider name, website, transport, jurisdiction-specific format, or the mere presence of a document in a regulatory repository.

**Examples.**

- a regulator issues a rule or notice;
- a filing is externally published as received;
- an authority publishes an enforcement decision; and
- a regulatory publication is corrected or withdrawn.

**Exclusions.**

- an issuer-originated disclosure merely relayed through a regulatory repository when the Classifying Fact is the issuer’s disclosure;
- legal advice or interpretation;
- a platform compliance determination;
- authorization or permission; and
- a recommendation or action.

### 6.7 Earnings Publication

**Meaning.** Earnings Publication represents an issuer-attributed release of financial-period results or explicitly stated earnings measures.

**Boundary.** Classification covers the publication event and qualifying issuer-reported results. It does not include platform calculations or conclusions derived from those results.

**Examples.**

- an issuer publishes quarterly revenue and earnings;
- an annual results release is issued; and
- an issuer revises a previously published result.

**Exclusions.**

- calculated growth or margins not directly source-reported;
- earnings surprise;
- quality scoring;
- consensus;
- forecasts or guidance treated as observed future fact;
- valuation; and
- investment judgment.

### 6.8 Market Status

**Meaning.** Market Status represents an externally reported current, scheduled, or effective state of a market, venue, auction, instrument session, or market calendar.

**Boundary.** The class reports external market state. It does not control the platform runtime or establish that an order may execute.

**Examples.**

- a venue reports a trading halt;
- a market reports that its regular session is open;
- an auction phase is published; and
- an official holiday calendar is issued.

**Exclusions.**

- runtime scheduling;
- job or workflow state;
- execution permission or eligibility;
- an inferred market regime;
- portfolio status; and
- a predicted closure or halt.

### 6.9 Macroeconomic Publication

**Meaning.** Macroeconomic Publication represents an attributable external publication of a macroeconomic measurement, revision, release, or reference period.

**Boundary.** The class preserves what was published and its temporal meaning. It does not infer economic regime, causality, or investment significance.

**Examples.**

- an official inflation measurement is released;
- a labor-market series is revised; and
- a central statistical publication states a reference period and value.

**Exclusions.**

- a macroeconomic forecast;
- scenario analysis;
- a derived regime;
- a trading signal;
- a recommendation; and
- an internally aggregated indicator.

### 6.10 News Publication

**Meaning.** News Publication represents an attributable external news publication event and the eligible fact-bearing report it contains.

**Boundary.** Classification records publication testimony. It does not establish truth, importance, causality, sentiment, or actionability.

**Examples.**

- a news report is published with attributable subject and issue time;
- a correction is published; and
- a report is retracted.

**Exclusions.**

- inferred sentiment;
- fact-checking or trust scores;
- an analyst report governed by Analyst Publication;
- a prediction, recommendation, or strategy;
- a platform summary that adds interpretation; and
- an alert triggered by the report.

### 6.11 Analyst Publication

**Meaning.** Analyst Publication represents the externally observable publication of analyst-authored material and only its qualifying fact-bearing statements.

**Boundary.** Observation may represent that analysis was published and preserve attributable eligible statements. It MUST NOT adopt analytical conclusions as platform fact or judgment.

**Examples.**

- an analyst report is issued;
- a published report changes its coverage status; and
- a correction to an analyst publication is released.

**Exclusions.**

- an analyst prediction treated as observed future state;
- a target price treated as Market Price;
- consensus calculated by the platform;
- endorsement of a rating;
- a recommendation; and
- Investment Judgment.

### 6.12 Sentiment Publication

**Meaning.** Sentiment Publication represents the attributable external fact that a source published a sentiment measurement or classification.

**Boundary.** The source-reported result and qualification may be represented without reproducing its derivation or adopting its analytical semantics.

**Examples.**

- an external source publishes a sentiment category;
- a source publishes a qualified sentiment measurement; and
- the source revises its published measurement.

**Exclusions.**

- platform-calculated sentiment;
- reproduction of a provider-private model;
- a prediction;
- a recommendation;
- a trading signal; and
- a strategy.

### 6.13 Alternative Data Observation

**Meaning.** Alternative Data Observation represents an attributable, externally measured real-world condition that is not governed by another existing Canonical Observation Class.

**Boundary.** This class is limited to direct external measurements and explicit source qualifications. It is not a catch-all for unclassified content, provider-specific products, or derived features.

**Examples.**

- an externally measured traffic count;
- an attributable weather measurement;
- a source-reported supply-chain activity measure; and
- an externally measured geospatial condition.

**Exclusions.**

- any fact already governed by another Canonical Observation Class;
- platform transformations or feature engineering;
- opaque scores without attributable external measurement meaning;
- inferences, forecasts, or conclusions;
- recommendations; and
- provider product names used as semantics.

## 7. Classification Rules

### 7.1 Qualification precedes classification

A candidate MUST first satisfy the complete M39-WP2 Observation Source and Observation Event boundary. Classification SHALL NOT make an otherwise ineligible claim eligible.

### 7.2 Exactly one outcome

At the constitutional boundary, classification has exactly three possible dispositions:

1. **One matching class:** the candidate MAY be admitted as an Observation Event of that class, subject to all other governance.
2. **Zero matching classes:** the candidate MUST NOT be admitted as a canonical Observation Event under this specification. A separately governed additive class is required.
3. **Multiple apparent matching classes:** the candidate is ambiguously bounded and MUST NOT be admitted in that form. Its Classifying Fact MUST be refined or split without changing source meaning.

These are specification dispositions, not runtime statuses, response values, API errors, or storage states.

### 7.3 Semantic granularity

Classification MUST occur at the single-fact granularity required by M39-WP2. A source artifact, document, feed item, message, or response is not necessarily one Observation Event.

Facts that can change, be corrected, be retracted, or retain meaning independently SHOULD be represented as distinct candidate events for classification. This rule defines semantic separability only and prescribes no implementation representation.

### 7.4 Mixed-content observations

When one source artifact contains facts belonging to different classes:

- each independently qualifying Classifying Fact MUST be evaluated separately;
- no event MAY receive multiple classes;
- excluded calculations, predictions, recommendations, strategies, and actions MUST remain excluded;
- publication of excluded content MAY be represented only to the extent permitted by M39-WP2, without adopting that content’s prohibited semantics; and
- splitting MUST preserve attribution, temporal meaning, uncertainty, correction, and provenance.

A publication event and a separately qualifying event described within the publication MAY receive different classes because they are different facts. They MUST NOT be duplicated as two classifications of the same fact.

### 7.5 Specific boundary before neighboring boundary

Classification MUST apply the exact semantic boundary, not the broadest ordinary-language label.

Accordingly:

- dividend semantics belong only to Dividend Event;
- split semantics belong only to Split Event;
- other corporate-action semantics belong only to Corporate Action;
- issuer-reported financial-period results belong only to Earnings Publication;
- other issuer disclosure semantics belong only to Corporate Disclosure;
- regulatory publication function belongs only to Regulatory Publication;
- source-reported sentiment belongs only to Sentiment Publication; and
- a direct external measurement belongs to Alternative Data Observation only when no other class governs it.

This is boundary application, not an implementation precedence algorithm.

### 7.6 Corrections, revisions, and retractions

A correction, revision, retraction, or later measurement is a new Observation Event under M39-WP2.

It MUST be classified according to the kind of fact it corrects, revises, retracts, or newly reports. Correction lifecycle alone SHALL NOT create a separate class. The earlier event’s classification and meaning MUST NOT change.

### 7.7 Origin and relay independence

Observation Origin and relay provenance MAY establish attribution or publication function, but MUST NOT classify by vendor identity.

The same origin MAY produce facts in multiple classes. The same class MAY be witnessed by multiple origins and relays. A provider-specific route, source product, endpoint, or field MUST NOT select the class.

### 7.8 Subject independence

Classification MUST NOT be inferred solely from asset type, issuer identity, venue, jurisdiction, portfolio membership, watchlist membership, or Registry classification.

An event MAY reference an existing canonical identity without transferring identity or classification authority from Asset Foundation.

### 7.9 Quality and truth independence

Source quality, confidence, disagreement, availability, and later validation MUST NOT change the semantic class of an event. They MAY qualify the evidence under existing governance.

Trust & Evaluation or another frozen owner MAY assess an event without reclassifying its represented fact.

### 7.10 No catch-all admission

No `OTHER`, `UNKNOWN`, provider-private, opaque, or implementation-default class is established by this specification.

Unknown meaning is not a kind of fact. A candidate lacking exactly one class remains unadmitted until its meaning is resolved or a separately approved additive class exists.

## 8. Relationship to M39-WP2 Source Boundary

M39-WP2 and M39-WP3 define orthogonal constitutional questions:

In the required boundary shorthand:

- Observation Source answers, “Who witnessed the fact?”
- Observation Classification answers, “What kind of fact is represented?”

M39-WP2 further distinguishes the source category from the Observation Origin responsible for the claim. That precision does not change the independence of source and classification.

| Dimension | Governing question | Governing authority | Must not determine |
| --- | --- | --- | --- |
| Observation Source | What kind of external witness can supply a qualifying claim? | M39-WP2 | Observation Class |
| Observation Origin | Who or what is responsible for the claim? | M39-WP2 | Observation Class by identity alone |
| Observation Classification | What kind of fact does this event represent? | M39-WP3 | Source eligibility or provider selection |
| Observation Payload | What provider-neutral fact content preserves the claim? | M39-WP2 and the separately governed class contract | Provider, runtime, transport, or storage behavior |

An eligible source does not make every output an Observation Event. An eligible event does not acquire a class from its source category. A valid class does not admit an ineligible source or prohibited payload.

Examples of independence include:

- a market-data source may publish both Market Price and Market Status facts;
- an issuer may originate Corporate Disclosure, Earnings Publication, Dividend Event, Split Event, or Corporate Action facts;
- a news relay may carry a Regulatory Publication without converting it into News Publication when the Classifying Fact remains the regulatory publication;
- a regulatory repository may relay an issuer-originated Corporate Disclosure without becoming the claim’s semantic class; and
- multiple unrelated providers may witness the same Market Price class without changing its meaning.

Source changes MUST remain invisible to class meaning. Class additions MUST NOT alter source eligibility rules.

## 9. Ownership Model

Every concept has exactly one semantic owner. Classification, reference, relay, custody, consumption, or presentation does not create shared ownership.

| Concept or boundary | Canonical owner | Classification relationship |
| --- | --- | --- |
| Observation Classification vocabulary | Market Intelligence | Sole owner of canonical class names and semantic boundaries |
| Classification of an Observation Event | Market Intelligence | Determines the one fact kind represented without acquiring adjacent-domain authority |
| Observation Source, Event, Payload, Timestamp, and Origin semantics | Market Intelligence under M39-WP2 | Remain unchanged and are referenced, not redefined |
| External source claim authorship | Observation Origin under M39-WP2 | Attribution does not own canonical class semantics |
| Asset identity and Registry classification | Asset Foundation | Event classification neither establishes nor changes asset identity or asset classification |
| External-fact ingestion toward ledger truth | Connectivity & Ingestion | Observation class does not create an ingestion proposal or truth-path authority |
| Transactions and financial truth | Ledger & Accounting | Observation class does not create, amend, or validate ledger truth |
| Portfolio derivations | Portfolio Intelligence | Portfolio meaning derived from observations remains outside classification |
| Investment conclusions and actions | Decision Intelligence and existing frozen action boundaries | Prediction, recommendation, strategy, intent, approval, and execution remain outside classification |
| Trust assessment | Trust & Evaluation | Quality or correctness assessment does not own or alter the event’s class |
| Authentication, authorization, approval, and human authority | Existing non-domain authority boundaries | Classification supplies no identity proof, permission, delegation, approval, or authority |
| Provider translation | Existing Market Data provider boundary | Source-specific translation does not own canonical classes |
| Runtime and storage | Existing operational and infrastructure owners | Invocation or custody does not own canonical classes |
| Experience composition | Experience Platform | Presentation labels and composition do not define or alter canonical class meaning |

No class grants authority to another domain, and no adjacent-domain consumption changes the class.

## 10. Extensibility and Future Class Admission

A future Canonical Observation Class MAY be admitted only through separately approved constitutional governance and only when all of the following are established:

1. The proposed fact kind satisfies every M39-WP2 qualification and exclusion.
2. Its meaning is not covered by any existing class.
3. Its boundary is mutually exclusive with every existing class.
4. Its name and meaning are provider-neutral.
5. It has one semantic responsibility.
6. It defines the Classifying Fact and required temporal meaning.
7. It defines treatment of uncertainty, absence, correction, revision, and retraction.
8. It preserves all existing ownership boundaries.
9. It introduces no calculation, analytics, prediction, recommendation, strategy, portfolio meaning, trading, execution, transaction, or authority.
10. It can coexist without changing any existing class, event classification, source boundary, consumer obligation, or frozen contract.
11. It does not require a provider, SDK, transport, storage system, API, or runtime mechanism to explain its meaning.
12. It receives separate authority before implementation or public exposure.

A future class MUST be additive. It MUST NOT:

- reinterpret or reclassify an existing event;
- carve semantic territory out of an existing class;
- convert an existing class into an abstract parent;
- rename, alias, deprecate, supersede, narrow, or widen an existing class;
- enter through a provider-private extension;
- use provider availability as justification for its boundary;
- introduce a catch-all class;
- alter M39-WP1 `price_kind` or any other frozen field;
- widen the M39-WP1 contract or public boundary;
- change M39-WP2 source eligibility; or
- require existing consumers to implement the new class to preserve current behavior.

If a proposed meaning overlaps an existing class, the proposal is not additive and SHALL NOT be admitted under this specification. If a provider offers a new label for an existing fact meaning, that label maps at the provider boundary to the existing class and does not create a new class.

## 11. Constitutional Invariants

The following rules are normative and cumulative.

### Semantic determinism

- **OC-01:** Every admitted Observation Event MUST have exactly one Canonical Observation Class.
- **OC-02:** Classification MUST be determined from the Classifying Fact at governed semantic granularity.
- **OC-03:** The same canonical fact meaning under the same ratified vocabulary MUST receive the same class.
- **OC-04:** Zero-class and multiple-class candidates MUST remain unadmitted in that form.
- **OC-05:** Classification Ambiguity MUST NOT be hidden by defaulting, guessing, source precedence, or multi-class assignment.

### Provider neutrality

- **OC-06:** Class semantics MUST be provider-neutral.
- **OC-07:** Provider names, products, SDK types, source field names, endpoints, protocols, formats, and infrastructure MUST NOT enter canonical class vocabulary.
- **OC-08:** Provider replacement, addition, removal, outage, or capability change MUST NOT alter class meaning.
- **OC-09:** Concrete source identity MAY remain provenance but MUST NOT act as a class discriminator.

### Semantic stability and additive evolution

- **OC-10:** Existing class names, boundaries, and event classifications MUST remain stable.
- **OC-11:** Future classes MUST be additive and mutually exclusive with every existing class.
- **OC-12:** A future class MUST NOT redefine, narrow, widen, rename, alias, supersede, or carve meaning from an existing class.
- **OC-13:** Unknown or unsupported meaning MUST NOT become a catch-all class.
- **OC-14:** Existing consumers MUST retain their current semantics when a future class is added.

### Ownership preservation

- **OC-15:** Market Intelligence MUST remain the sole semantic owner of Observation Classification.
- **OC-16:** Classification MUST NOT transfer identity, Registry, ingestion, ledger, portfolio, decision, Trust, authorization, execution, provider, runtime, storage, or Experience authority.
- **OC-17:** Consumption, relay, custody, rendering, or evaluation MUST NOT transfer class ownership.
- **OC-18:** Observation Classification MUST remain evidence classification and MUST NOT become truth, quality, importance, suitability, or action classification.

### Separation and single responsibility

- **OC-19:** One Observation Event MUST represent one Classifying Fact and one class.
- **OC-20:** Mixed-content source artifacts MUST be separated at independently meaningful fact boundaries or remain unadmitted.
- **OC-21:** Classification MUST NOT perform calculation, inference, prediction, recommendation, strategy, authorization, trading, execution, transaction processing, portfolio evaluation, or state mutation.
- **OC-22:** Classification MUST remain independent of runtime, transport, storage, cache, API, and implementation behavior.
- **OC-23:** Corrections, revisions, retractions, and later measurements MUST NOT mutate an earlier event or its classification.
- **OC-24:** M38, M39-WP1, and M39-WP2 contracts MUST remain unchanged.

## 12. Prohibited Interpretation

This specification SHALL NOT be interpreted to:

- authorize any class for implementation;
- require a class field in any existing or future contract;
- define enum values, wire tokens, schemas, tables, indexes, or storage keys;
- define provider mappings or adapter behavior;
- define runtime branching, dispatch, routing, fallback, or orchestration;
- define API exposure or response behavior;
- classify a provider rather than a fact;
- classify an asset, transaction, portfolio, recommendation, order, or user;
- treat source category as event class;
- treat `price_kind` as an Observation Classification field;
- treat class membership as evidence quality or truth;
- treat Corporate Action as including Dividend Event or Split Event;
- treat Corporate Disclosure as including Earnings Publication or dedicated corporate-event semantics;
- treat Alternative Data Observation as a generic fallback;
- admit predictions, recommendations, strategies, or derived analytics as observed fact; or
- reopen or amend a completed milestone.

No informative example creates an exception to a normative boundary.

## 13. Informative Examples

This section is informative. The normative rules remain in §§4–12.

### 13.1 Valid classifications

| External fact represented | Classification | Reason |
| --- | --- | --- |
| An official source reports an asset’s closing value | Market Price | The Classifying Fact is an externally reported market value |
| An issuer declares a distribution with ex-date and payment date | Dividend Event | The fact is a dividend declaration with explicit terms |
| An issuer announces a reverse split ratio | Split Event | The fact is a split announcement |
| An issuer announces tender-offer terms | Corporate Action | The action is neither a dividend nor a split |
| An issuer publishes a non-earnings operational update | Corporate Disclosure | The fact is issuer disclosure outside more specific classes |
| An issuer releases quarterly results | Earnings Publication | The fact is publication of financial-period results |
| A regulator issues an enforcement notice | Regulatory Publication | The represented fact is a regulatory publication |
| A venue reports that trading is halted | Market Status | The represented fact is external market state |
| A statistical authority revises an inflation series | Macroeconomic Publication | The represented fact is a macroeconomic publication and revision |
| A news organization publishes and later corrects a report | News Publication for each event | Publication and correction are distinct attributed news events |
| An analyst organization issues a report | Analyst Publication | The represented fact is the attributable publication event |
| An external source publishes a qualified sentiment measure | Sentiment Publication | The represented fact is that source’s sentiment publication |
| A measurement source reports a traffic count | Alternative Data Observation | It is a direct external measurement not governed elsewhere |

### 13.2 Invalid classifications

| Candidate | Invalid treatment | Resolution |
| --- | --- | --- |
| Provider-specific quote object | Classifying by SDK type as Market Price | Establish provider-neutral price meaning first or do not admit it |
| Predicted next-week price | Market Price | Prediction remains excluded |
| Analyst target price | Market Price | At most the eligible publication fact may be Analyst Publication; the target is not observed market value |
| Dividend cash credited to an account | Dividend Event | The credit is a Ledger & Accounting fact |
| Calculated portfolio value | Market Price | It is a Portfolio Intelligence derivation |
| Internal sentiment score | Sentiment Publication | It is platform-derived analytics |
| Unknown provider payload | Alternative Data Observation | No class is a catch-all; the candidate remains unadmitted |
| Venue halt used as order permission | Market Status plus execution authority | Market Status grants no execution authority |
| Regulatory filing interpreted as legal compliance | Regulatory Publication plus compliance conclusion | Preserve publication evidence; legal or compliance meaning remains outside Observation |

### 13.3 Mixed-content examples

**Earnings release with dividend declaration.** The release artifact contains at least two independently meaningful facts. The financial-period result is an Earnings Publication event. The dividend declaration is a Dividend Event. Neither event receives two classes.

**Issuer announcement of a split with management commentary.** The split terms are a Split Event. Qualifying non-split issuer disclosure may be a separate Corporate Disclosure event. Predictions or recommendations in commentary remain excluded.

**News report relaying a regulatory decision.** If the Classifying Fact is that the news report was published, it is News Publication. If a separate event faithfully represents the regulator’s publication, it is Regulatory Publication. Relay provenance does not turn one fact into two classes.

**Analyst report containing a target and source-reported sentiment.** The publication event may be Analyst Publication. The target remains excluded from Market Price. A sentiment result qualifies as Sentiment Publication only when represented as a distinct attributable source-reported measurement under M39-WP2.

### 13.4 Ambiguous cases and resolution

**Issuer filing in a regulatory repository.** Repository location does not decide the class. An issuer-originated disclosed fact remains Corporate Disclosure or Earnings Publication according to content. A separate fact that the regulator received or issued a publication may be Regulatory Publication.

**Externally published proprietary index.** If the represented fact is an attributable external market value with explicit meaning, Market Price may apply. If it is a source-published analytical or sentiment classification, the applicable publication class may apply. If the meaning is opaque, no class applies.

**Corporate event with both split and distribution terms.** The artifact is not one multi-class event. Split terms are classified as Split Event and distribution terms as Dividend Event when each qualifies independently.

**Alternative measurement associated with an issuer.** Issuer association does not make the fact Corporate Disclosure. A direct external real-world measurement not published by the issuer and not governed by another class is Alternative Data Observation.

**Source disagreement.** Two sources reporting different values do not create different classes. Each qualifying event remains in the class determined by its fact meaning, while disagreement remains explicit evidence for its existing owner to assess.

## 14. Conformance and Independent Review

A future specification, implementation proposal, or class-extension proposal conforms to M39-WP3 only when objective review establishes every requirement below.

| Identifier | Required proof |
| --- | --- |
| CLS-01 | Every admitted Observation Event maps to exactly one class defined in §6 or separately admitted under §10 |
| CLS-02 | Zero-match candidates remain unadmitted and do not enter an `OTHER` or `UNKNOWN` class |
| CLS-03 | Multiple-match candidates are refined or separated without silent precedence or multi-class assignment |
| CLS-04 | Classification follows the Classifying Fact at M39-WP2 semantic granularity |
| CLS-05 | Dividend, Split, Corporate Action, Corporate Disclosure, and Earnings boundaries are non-overlapping |
| CLS-06 | Publication events remain distinct from independently qualifying published-content facts |
| SRC-01 | Source Category, Observation Origin, and Observation Classification remain independent under §8 |
| SRC-02 | No source or provider identity determines class meaning |
| PRV-01 | No provider, product, SDK, field, endpoint, transport, format, or infrastructure concept enters canonical class vocabulary |
| SEM-01 | Equivalent canonical fact meaning receives the same class across qualifying sources |
| SEM-02 | Class membership expresses fact kind only and does not express truth, quality, importance, suitability, availability, or authority |
| SEM-03 | Corrections, revisions, retractions, and later measurements preserve earlier event meaning and classification |
| OWN-01 | Market Intelligence remains the sole semantic owner of Observation Classification |
| OWN-02 | Every adjacent constitutional and non-domain authority boundary retains its prior ownership |
| SEP-01 | Mixed-content artifacts are separated at independent fact boundaries |
| SEP-02 | No class admits calculations, analytics, predictions, recommendations, strategies, trading, execution, transactions, or portfolio meaning |
| EXT-01 | A proposed future class is distinct from and mutually exclusive with every existing class |
| EXT-02 | A future class is additive and changes no existing name, boundary, event classification, or consumer obligation |
| EXT-03 | A future class has separate constitutional approval before implementation or exposure |
| CMP-01 | M38 contracts remain unchanged |
| CMP-02 | M39-WP1 contract, `price_kind`, public boundary, availability, derivation, normalization, feature, and execution-separation rules remain unchanged |
| CMP-03 | M39-WP2 definitions, source qualification, exclusions, ownership, and extension rules remain unchanged |
| SCP-01 | The proposal grants no implementation, provider, runtime, storage, transport, API, or public-exposure authority |

The independent reviewer SHALL verify:

- constitutional consistency;
- complete compatibility with M38, M39-WP1, and M39-WP2;
- provider and mechanism neutrality;
- deterministic single-class assignment;
- non-overlapping class boundaries;
- correct mixed-content separation;
- deterministic ownership;
- additive future extensibility;
- absence of catch-all admission;
- absence of implementation, runtime, transport, storage, or API assumptions; and
- absence of implicit implementation authorization.

Conformance establishes constitutional classification validity only. It does not approve a provider, implementation, runtime, storage model, transport, API, migration, feature activation, or public contract.

## 15. Canonical Closure

M39-WP3 defines the constitutional classification model for future Market Observation work.

After ratification:

- every admitted Observation Event MUST have exactly one canonical class;
- source eligibility and event classification MUST remain independent;
- all initial class boundaries MUST remain stable;
- future classes MUST be additive and separately approved;
- provider and mechanism changes MUST remain invisible to class meaning;
- M38, M39-WP1, and M39-WP2 MUST remain authoritative and unchanged; and
- no class definition SHALL be treated as implementation authorization.

Nothing in this specification reopens a completed milestone, modifies a frozen contract, or authorizes implementation.
