# M41-WP2 Stage B — Subject and Manifest Contract Specification

**Date:** 2026-07-24

**Milestone:** M41 — Governed Market Measure Semantics

**Work package:** M41-WP2

**Stage:** B — Subject and Manifest Contract Specification

**Document class:** Normative semantic contract specification

**Status:** `COMPLETE_FOR_INDEPENDENT_REVIEW`

**Architecture authority:** Frozen M41 Architecture and confirmed M41-WP2
Architecture

**Vocabulary authority:** Confirmed M41-WP1 and confirmed M41-WP2 Stage A

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Production method authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API and public-exposure authority:** `NONE`

---

## 1. Executive Summary

This specification makes the already-confirmed Measure Subject, Observation
Input Manifest, and Manifest Entry vocabulary mechanically precise without
changing their meaning, ownership, or architectural placement.

It fixes:

- the three closed Measure Subject record shapes, their identity, ordering,
  immutability, and canonical byte serialization;
- the Observation Input Manifest's identity, canonical composition, binding
  to one exact Measure Subject, and canonical byte serialization;
- the fields and invariants of each Manifest Entry;
- evidence-equivalence and evidence-conflict rules over exact frozen M39
  Observation evidence;
- fail-closed validation and error conditions; and
- field-level ownership-boundary gates and compatibility requirements.

Measure Subject, Observation Input Manifest, and Manifest Entry are owned
solely by Market Intelligence. Asset Foundation remains the sole owner of
every cited `asset_id`. M39 remains authoritative for every referenced
Observation's identity and meaning. Reference creates no shared ownership.

The field labels, shape tags, byte tags, lengths, and comparison operations
in this document are ordinary contract syntax. They are not additional
governed vocabulary. This specification grants no implementation, runtime,
provider, persistence, retrieval, or API authority.

---

## 2. Scope

### 2.1 Included

This specification governs only:

1. Measure Subject record construction for the three shapes already closed
   by M41-WP1;
2. Measure Subject identity, canonical ordering, and canonical
   serialization;
3. Observation Input Manifest purpose, record structure, identity, binding,
   ordering, and canonical serialization;
4. Manifest Entry structure, identity within a manifest, ownership, and
   invariants;
5. equivalence and conflict determination for candidate M39 Observation
   evidence;
6. validation and error conditions for these three contracts; and
7. the compatibility and ownership boundaries required by M34, M39, M40,
   frozen M41 Architecture, frozen M41-WP1, and confirmed M41-WP2
   Architecture.

### 2.2 Excluded

This specification does not:

- alter any frozen architecture or M41-WP1 contract;
- alter a Stage A admission or merge disposition;
- define Measurement Window, Measure Value, Market Measure Result,
  Provenance composition, or degraded-state interaction;
- redefine Computation Outcome;
- define a formula, calculation procedure, production method, or service;
- authorize construction, selection, retrieval, execution, storage,
  history, replay, caching, transport, or provider access;
- define a database, schema, index, message, endpoint, SDK, or public API;
- define provider-specific identifiers, payloads, priority, fallback, or
  reconciliation;
- add Asset Definition Version to Measure Subject;
- include Asset Foundation reference data, explicit invocation parameters,
  or explicit governed calculation dependencies in an Observation Input
  Manifest or Manifest Entry; or
- rank evidence, judge correctness or quality, select a preferred source, or
  create Investment Judgment.

### 2.3 Authority and precedence

This specification is subordinate, in order, to:

1. frozen platform and Asset Foundation architecture;
2. frozen M34 decisions and frozen M39/M40 specifications;
3. frozen M41 Architecture;
4. frozen M41-WP1 Stage 1, Stage 2, and Closeout;
5. confirmed M41-WP2 Architecture; and
6. confirmed M41-WP2 Stage A.

If this document conflicts with a higher authority, the higher authority
governs and the conflicting clause is invalid. No such conflict is intended.

### 2.4 Normative language

`MUST`, `MUST NOT`, `REQUIRED`, `SHALL`, `SHALL NOT`, `SHOULD`, `SHOULD NOT`,
and `MAY` are normative. Lowercase uses are explanatory.

---

## 3. Normative Definitions

### 3.1 Measure Subject

A Measure Subject is exactly one of the following three closed subject shapes
to which one Market Measure Definition / Method Version invocation applies:

1. a single canonical Asset identity reference;
2. an ordered, canonical reference set of two or more Asset identities; or
3. an explicit market-context parameter set with no Asset identity
   reference.

A Measure Subject MUST instantiate exactly one shape. A hybrid containing
both Asset identity and market-context parameters is invalid. It references
Asset Foundation identity without mutation, derivation, or reinterpretation
and carries no ledger, portfolio, life-context, judgment, or evaluation
meaning.

### 3.2 Observation Input Manifest

An Observation Input Manifest is an immutable, complete, deterministically
ordered evidence binding that enumerates the exact frozen M39 Observation
semantics selected as calculation inputs. It is evidence lineage, not an
Observation, provider request, persistence model, retrieval permission, or
production claim.

Every referenced Observation retains its frozen M39 identity and meaning.
Manifest membership does not create, correct, merge, or supersede an
Observation.

### 3.3 Manifest Entry

A Manifest Entry is one immutable, named constituent element of a resolved
Observation Input Manifest, consisting of exactly one immutable reference to
a frozen M39 Observation and that Observation's declared role within the
binding Method Requirement's prerequisite evaluation.

It is a coordinate within Observation Input Manifest composition, not a new
manifest-level axis or evidence category. It carries no Asset Foundation
reference data, invocation parameter, or governed calculation dependency.
It creates, corrects, merges, or supersedes no Observation.

### 3.4 Ordinary serialization terms

For this specification only:

- a **text value** is a finite, non-empty sequence of Unicode scalar values
  encoded as UTF-8;
- an **opaque reference value** is a finite, non-empty canonical reference
  supplied by the authority that owns the referenced identity;
- `u32` is an unsigned 32-bit integer encoded in network byte order;
- `lp(x)` is `u32(byte_length(x))` followed by the bytes of `x`;
- unsigned byte order compares bytes left-to-right as integers from `0` to
  `255`, with a proper prefix ordered before the longer sequence; and
- canonical bytes are the exact bytes produced by §§4.7 and 5.8.

These phrases and functions are ordinary syntax local to this contract. They
do not create governed nouns, ownership, persistence formats, or API formats.

Text values MUST already be in the exact form declared by their owning
contract. This specification performs no case folding, whitespace trimming,
Unicode normalization, alias expansion, identifier resolution, or provider
translation.

---

## 4. Measure Subject Contract Specification

### 4.1 Purpose and owner

Measure Subject names the exact, canonical binding of one Market Measure
invocation to one or more Assets or to an explicitly defined market context.

Market Intelligence is the sole owner of the Measure Subject binding
contract. Asset Foundation remains the sole owner of every referenced
`asset_id`, Asset definition, and Asset classification.

### 4.2 Common canonical field

Every Measure Subject MUST contain exactly one `shape` field with exactly one
of these ASCII values:

| `shape` value | Closed meaning |
| --- | --- |
| `single_asset` | One canonical Asset identity |
| `asset_set` | An ordered canonical set of at least two Asset identities |
| `market_context` | A non-empty explicit parameter set containing no Asset identity |

The field names and token values in this table are serialization syntax, not
new governed vocabulary.

### 4.3 `single_asset` structure

A `single_asset` Measure Subject MUST contain exactly:

| Field | Cardinality | Requirement |
| --- | ---: | --- |
| `shape` | 1 | Exact value `single_asset` |
| `asset_id` | 1 | Exact, immutable Asset Foundation `asset_id` |
| `role` | 1 | Non-empty, explicit, measure-declared subject role |

It MUST contain no `assets` collection and no market-context parameter.
Ticker, display symbol, provider identifier, alias, or dynamically resolved
value MUST NOT substitute for `asset_id`.

### 4.4 `asset_set` structure

An `asset_set` Measure Subject MUST contain exactly:

| Field | Cardinality | Requirement |
| --- | ---: | --- |
| `shape` | 1 | Exact value `asset_set` |
| `assets` | 1 collection | Two or more immutable elements |
| `assets[].asset_id` | 1 per element | Exact Asset Foundation `asset_id` |
| `assets[].role` | 1 per element | Non-empty, explicit, measure-declared subject role |

The pair (`asset_id`, `role`) MUST be unique within the Measure Subject.
The same `asset_id` MAY occur under more than one distinct role only when the
governing Market Measure Definition explicitly requires those distinct
roles. Otherwise repetition is invalid.

The collection MUST contain no market-context parameter and no Asset
Definition Version.

### 4.5 `market_context` structure

A `market_context` Measure Subject MUST contain exactly:

| Field | Cardinality | Requirement |
| --- | ---: | --- |
| `shape` | 1 | Exact value `market_context` |
| `parameters` | 1 collection | One or more explicit name/value elements |
| `parameters[].name` | 1 per element | Non-empty declared parameter name |
| `parameters[].value` | 1 per element | Non-empty canonical value under the declaring measure contract |

Each parameter name MUST be unique. Every name and value MUST be explicit;
an ambient default, unresolved placeholder, current time, `latest`, provider
value, or mutable process state is invalid.

This shape MUST contain no `asset_id`, no `assets` collection, and no value
that purports to be an Asset alias or shadow identity.

### 4.6 Canonical identity and ordering

Two Measure Subject records denote the same Measure Subject if and only if
their canonical bytes under §4.7 are byte-identical.

Canonical ordering is part of the already-confirmed Measure Subject
obligation:

1. In `asset_set`, elements MUST be sorted first by the UTF-8 bytes of
   `asset_id` and then by the UTF-8 bytes of `role`, both in unsigned byte
   order.
2. In `market_context`, elements MUST be sorted first by the UTF-8 bytes of
   `name` and then by the UTF-8 bytes of `value`, both in unsigned byte
   order.
3. Input presentation order has no identity effect. A conforming serializer
   sorts before serialization.
4. Duplicate composite pairs in `asset_set` and duplicate parameter names in
   `market_context` are errors; they are not silently removed.

The Measure Subject and Observation Input Manifest use the same underlying
ordering discipline: lexicographic unsigned-byte comparison of their
contract-defined canonical key components. Their key components differ
because their records mean different things. There is no second ordering
concept and no ownership change.

### 4.7 Canonical serialization

Every Measure Subject MUST serialize as:

```text
ASCII("MSB1")
shape_tag
shape_body
```

`shape_tag` is one byte:

| Shape | Byte |
| --- | --- |
| `single_asset` | `0x01` |
| `asset_set` | `0x02` |
| `market_context` | `0x03` |

The shape body is:

```text
single_asset:
  lp(UTF8(asset_id))
  lp(UTF8(role))

asset_set:
  u32(element_count)
  repeat in §4.6 canonical order:
    lp(UTF8(asset_id))
    lp(UTF8(role))

market_context:
  u32(parameter_count)
  repeat in §4.6 canonical order:
    lp(UTF8(name))
    lp(UTF8(value))
```

No byte-order mark, terminator, padding, optional field, unknown extension,
or trailing byte is permitted. `MSB1` is a contract-version tag, not a Method
Version, Asset Definition Version, or governed semantic version.

Canonical serialization MUST be injective: one valid logical Measure Subject
has exactly one byte sequence, and one valid byte sequence reconstructs
exactly one logical Measure Subject.

### 4.8 Invariants

1. Exactly one closed shape is present.
2. Every Asset reference is an exact immutable `asset_id`.
3. No shape contains an Asset Definition Version.
4. No hybrid Asset/market-context record is valid.
5. Multi-Asset and parameter collections are canonical sets under §4.6.
6. Identity is independent of source-record order, custody, storage,
   provider, display, and runtime state.
7. Once specified, every identity-bearing field is immutable. Any change
   produces a different Measure Subject.
8. Measure Subject grants no Asset capability and authorizes no action.
9. No field carries Ledger, Portfolio, Wealth, judgment, trust, quality,
   recommendation, suitability, or presentation meaning.

---

## 5. Observation Input Manifest Contract Specification

### 5.1 Purpose and owner

The Observation Input Manifest binds the complete exact set of frozen M39
Observation evidence selected as inputs for one exact Measure Subject under
one bound Market Measure Definition / Method Version applicability contract.

Market Intelligence is its sole owner.

### 5.2 Canonical structure

An Observation Input Manifest MUST contain exactly:

| Field | Cardinality | Requirement |
| --- | ---: | --- |
| `subject` | 1 | One complete valid Measure Subject |
| `entries` | 1 collection | Zero or more valid Manifest Entry records |

`subject` MUST be represented by the exact canonical bytes from §4.7.
`entries` MUST contain only exact M39 Observation evidence membership.

An empty `entries` collection is valid only when the bound Market Measure
Definition and Method Requirement set permit zero M39 Observation evidence.
It never implies missing, deferred, dynamically retrievable, or `latest`
evidence.

### 5.3 Manifest Entry canonical structure

Each Manifest Entry MUST contain exactly:

| Field | Cardinality | Requirement |
| --- | ---: | --- |
| `requirement_key` | 1 | Exact key of one binding Method Requirement whose prerequisite category is Observation category availability |
| `observation_identity` | 1 | Exact immutable reference to one admitted frozen M39 Observation Identity |

The `requirement_key` is the Observation's declared role in prerequisite
evaluation. It MUST resolve to a Method Requirement in the bound Method
Version and MUST NOT be an invented label, formula role, provider role, or
presentation role.

The `observation_identity` value is opaque to this specification. It MUST be
the canonical reference recognized by M39 authority. It MUST NOT be a
provider record identifier, request identifier, message identifier, ticker,
symbol, storage key, or inferred tuple.

### 5.4 Relationship rules

1. Every Observation Input Manifest binds exactly one Measure Subject.
2. Every Manifest Entry belongs to exactly one Observation Input Manifest.
3. Every Manifest Entry references exactly one frozen M39 Observation.
4. A Manifest Entry MUST reference exactly one applicable
   Observation-category Method Requirement through `requirement_key`.
5. A referenced Observation MAY support more than one applicable Method
   Requirement. Each distinct (`requirement_key`, `observation_identity`)
   pair is then a distinct Manifest Entry.
6. Repetition of an identical pair is invalid.
7. `ObservationEvidenceCount` MUST be derived from the frozen M41-WP1
   wording as follows:
   - Manifest Entry did not exist when M41-WP1 froze.
   - M41-WP1 therefore could not have used “M39 Observation evidence
     records” to mean Manifest Entries.
   - The frozen phrase necessarily refers to the underlying admitted M39
     Observation evidence itself, identified by its M39 Observation
     identity.
   - Repetition of one Observation identity across multiple requirement
     roles creates multiple Manifest Entries but does not create additional
     M39 Observation evidence records.
   - `ObservationEvidenceCount` therefore MUST equal the count of distinct
     referenced M39 Observation identities in the entire manifest.
8. Membership changes neither the referenced Observation nor the bound
   Measure Subject.

### 5.5 Binding rules

A valid binding MUST satisfy all of the following:

1. The exact Market Measure Definition revision and exact Method Version are
   fixed outside the Measure Subject and Observation Input Manifest.
2. The Measure Subject's shape is within the Market Measure Definition's
   declared subject-shape subset.
3. The Market Measure Definition's permitted input-category declaration
   includes M39 Observation evidence when `entries` is non-empty.
4. Every `requirement_key` resolves within the bound Method Version to a
   Method Requirement whose prerequisite category is Observation category
   availability.
5. Every referenced Observation is already admitted under frozen M39 and is
   cited by exact immutable Observation Identity.
6. `ObservationEvidenceCount` is calculated as specified in §5.4(7), and
   every Observation-category evaluation rule is evaluated without
   substitution or heuristic.
7. Every applicable Method Requirement evaluates to `MET`. An `UNMET`
   requirement makes the supplied input set insufficient under the frozen
   M41-WP1 applicability contract.
8. Every Manifest Entry is necessary to the declared resolved binding. An
   unrelated, undeclared, or surplus entry makes the manifest non-conforming;
   it is not retained as optional evidence.
9. Asset Foundation reference data, explicit invocation parameters, and
   explicit governed calculation dependencies are validated through their
   separately owned binding coordinates. They MUST NOT appear as Manifest
   Entries.
10. No binding step MAY dynamically choose `latest`, query a provider,
    prefer a source, or repair an Observation.

### 5.6 Evidence equivalence and conflict

Candidate representations are **identity-equivalent** only when frozen M39
determines that they unambiguously denote the same admitted Observation
Event and therefore preserve one Observation Identity. Different faithful
representations of that one identity resolve to one Manifest Entry for a
given `requirement_key`.

Equal payload values, similar meaning, a shared origin, a provider reference,
or semantic equivalence between identity-distinct Observation Events MUST NOT
collapse their identities. Identity-distinct Observations remain distinct
evidence and, when all requirements permit it, MAY both appear.

An evidence conflict exists only when all of the following are true:

1. two or more candidate Observations are identity-distinct under M39;
2. they are candidates for the same applicable `requirement_key`;
3. their frozen M39 meanings are materially incompatible on the same
   calculation-relevant semantic coordinate; and
4. the applicable prerequisite requires one unambiguous input set and cannot
   be satisfied by retaining all candidates as distinct evidence.

A conflict MUST NOT be silently resolved by order, source priority,
provider preference, recency, payload comparison, quality score, or
correctness judgment. The binding is unresolved and maps only to the existing
`INSUFFICIENT_INPUT` Computation Outcome meaning: the canonical supplied
inputs do not satisfy the declared input prerequisites.

This clause does not create a new Computation Outcome, define Market Measure
Result composition, or authorize Trust & Evaluation activity.

### 5.7 Canonical identity and ordering

Two Observation Input Manifests denote the same semantic evidence binding if
and only if their canonical bytes under §5.8 are byte-identical.

Before serialization, Manifest Entries MUST be sorted:

1. first by the UTF-8 bytes of `requirement_key`; and
2. then by the bytes of the canonical `observation_identity` reference;
3. using unsigned byte order for both comparisons.

Presentation order has no identity effect. Duplicate composite pairs are
errors and MUST NOT be silently removed.

This is the same underlying canonical ordering discipline used by Measure
Subject in §4.6, applied to Manifest Entry's own contract-defined components.

### 5.8 Canonical serialization

Every Observation Input Manifest MUST serialize as:

```text
ASCII("OIM1")
lp(subject_canonical_bytes)
u32(entry_count)
repeat in §5.7 canonical order:
  lp(UTF8(requirement_key))
  lp(observation_identity_canonical_reference_bytes)
```

No byte-order mark, terminator, padding, optional field, unknown extension,
or trailing byte is permitted. `OIM1` is a contract-version tag only.

The embedded Measure Subject bytes MUST independently validate under §4.7.
The manifest encoding MUST be injective and round-trippable without external
ordering or default rules.

### 5.9 Invariants

1. The manifest is immutable, complete, enumerable, and canonically ordered.
2. It binds exactly one valid Measure Subject.
3. Membership is limited to exact frozen M39 Observation evidence.
4. Every Manifest Entry has exactly one applicable requirement role and one
   exact Observation identity.
5. No dynamic `latest` reference or unresolved reference is present.
6. Referenced M39 identity and meaning are preserved without correction,
   merge, supersession, or reinterpretation.
7. Manifest identity is independent of presentation order, provider, custody,
   storage, transport, and runtime state.
8. Evidence conflict fails closed as `INSUFFICIENT_INPUT`; no silent choice is
   permitted.
9. The manifest grants no provider access, retrieval permission, production
   existence, or execution authority.
10. No field carries Ledger, Portfolio, Wealth, judgment, evaluation,
    quality, suitability, recommendation, or presentation meaning.

---

## 6. Ownership Boundaries

### 6.1 Singular ownership matrix

| Semantic concern | Sole owner | This specification's rule |
| --- | --- | --- |
| Measure Subject binding and its ordering obligation | Market Intelligence | Defined structurally here; no shared ownership |
| Observation Input Manifest | Market Intelligence | Existing ownership preserved |
| Manifest Entry | Market Intelligence | Confirmed Stage A admission preserved |
| Canonical Asset identity, definition, and classification | Asset Foundation | `asset_id` cited exactly; never recreated or reinterpreted |
| M39 Observation identity and meaning | Market Intelligence under frozen M39 | Referenced exactly; never changed by membership |
| Method Requirement and Method Version applicability | Market Intelligence under frozen M41-WP1 | Cited by exact field; never renamed or reattributed |
| Ledger and accounting truth | Ledger & Accounting | Excluded |
| Portfolio facts and derivations | Portfolio Intelligence | Excluded |
| Judgment, forecast, recommendation, and action intent | Decision Intelligence | Excluded |
| Correctness, reliability, quality, and evaluator verdict | Trust & Evaluation | Excluded |
| Presentation and interaction state | Experience Platform | Excluded |
| Provider interaction and translation | Existing Provider Layer | No authority granted |
| Runtime, persistence, API, and public exposure | Existing architectural owners | No authority granted |

Reference, custody, serialization, validation, or transport MUST NOT create
shared ownership or transfer semantic authority.

### 6.2 Field-level five-part ownership-boundary gate

| Contract field | Permitted subject | Permitted inputs | Output meaning | Ledger / Portfolio / Wealth exclusion | Judgment exclusion | Result |
| --- | --- | --- | --- | --- | --- | --- |
| Measure Subject `shape` | One closed subject shape | Frozen three-value closure | Identifies record variant only | Structural exclusion | No verdict or forecast | Pass |
| `asset_id` | Canonical Asset | Exact Asset Foundation identity | Cites identity only | No financial or portfolio fact | No quality or preference | Pass |
| Asset `role` | Measure-declared subject role | Explicit canonical text | Distinguishes subject participation | No holding, lot, or life context | No recommendation | Pass |
| `assets` | Two or more canonical Assets | Exact `asset_id` and role pairs | Ordered subject composition | No portfolio membership meaning | No ranking or selection | Pass |
| `parameters` | Explicit market context | Declared canonical name/value pairs | Names market context only | No person, household, goal, or portfolio | No outlook or suitability | Pass |
| Manifest `subject` | One Measure Subject | Exact §4 canonical bytes | Binds evidence to subject | Inherits Measure Subject exclusions | Inherits Measure Subject exclusions | Pass |
| Manifest `entries` | Evidence binding | Manifest Entry only | Complete selected evidence set | No ledger or portfolio input | No preferred-evidence judgment | Pass |
| `requirement_key` | One applicable Method Requirement | Exact WP1 key | Declares prerequisite role | No financial-truth meaning | No quality meaning | Pass |
| `observation_identity` | One frozen M39 Observation | Exact immutable M39 identity | Cites evidence only | No ledger or portfolio mutation | No truth or correctness verdict | Pass |

All fields pass. No field creates an owner beyond the singular ownership
matrix in §6.1.

---

## 7. Validation Requirements

### 7.1 Measure Subject validation

A validator MUST reject a Measure Subject unless:

1. the contract tag, shape tag, field sequence, lengths, and end-of-record
   boundary are exact;
2. exactly one closed shape is instantiated;
3. all required fields are present and no additional field is present;
4. every `asset_id` is an exact, immutable Asset Foundation identity;
5. every required role or parameter value is explicit and non-empty;
6. cardinality and uniqueness rules are satisfied;
7. collection order is canonical or can be canonically reconstructed without
   loss;
8. no Asset Definition Version, provider-shaped identity, `latest`, ambient
   default, or forbidden-domain value is present; and
9. decode followed by encode reproduces byte-identical canonical bytes.

### 7.2 Manifest and Manifest Entry validation

A validator MUST reject an Observation Input Manifest unless:

1. its embedded Measure Subject is valid;
2. its entry count equals its decoded Manifest Entry count;
3. every Manifest Entry has exactly the two fields in §5.3;
4. every requirement key resolves to an applicable Observation-category
   Method Requirement in the exact bound Method Version;
5. every Observation identity resolves under frozen M39 authority to exactly
   one admitted immutable Observation Event;
6. every composite pair is unique and the collection is canonically ordered;
7. distinct-identity counting applies the mandatory derivation in §5.4(7);
8. every applicable prerequisite evaluates to `MET`;
9. no evidence conflict under §5.6 remains;
10. exact evidence reproduction preserves every referenced Observation's
    frozen identity and meaning; and
11. decode followed by encode reproduces byte-identical canonical bytes.

### 7.3 Error conditions

| Code | Condition | Required disposition |
| --- | --- | --- |
| `SB-SUBJECT-001` | Missing, unknown, or multiple Measure Subject shapes | Reject |
| `SB-SUBJECT-002` | Shape field or cardinality violation | Reject |
| `SB-SUBJECT-003` | Non-canonical, unresolved, dynamic, or provider-shaped Asset reference | Reject |
| `SB-SUBJECT-004` | Hybrid Asset and market-context content | Reject |
| `SB-SUBJECT-005` | Duplicate or non-canonical collection element | Reject |
| `SB-SUBJECT-006` | Asset Definition Version appears inside Measure Subject | Reject |
| `SB-SUBJECT-007` | Invalid or non-round-trippable subject bytes | Reject |
| `SB-MANIFEST-001` | Invalid or absent bound Measure Subject | Reject |
| `SB-MANIFEST-002` | Manifest Entry has missing, additional, or invalid field | Reject |
| `SB-MANIFEST-003` | Requirement key is absent, inapplicable, or not Observation-category | Reject |
| `SB-MANIFEST-004` | Observation identity is unresolved, mutable, non-M39, or provider-shaped | Reject |
| `SB-MANIFEST-005` | Duplicate or non-canonically ordered Manifest Entry | Reject |
| `SB-MANIFEST-006` | Manifest includes a forbidden non-M39 input category | Reject |
| `SB-MANIFEST-007` | Applicable Method Requirement evaluates to `UNMET` | Input insufficient under frozen WP1 |
| `SB-MANIFEST-008` | Evidence conflict remains unresolved | `INSUFFICIENT_INPUT` only |
| `SB-MANIFEST-009` | Dynamic `latest`, implicit default, or silent evidence choice | Reject |
| `SB-MANIFEST-010` | Invalid or non-round-trippable manifest bytes | Reject |
| `SB-BOUNDARY-001` | Ledger, Portfolio, Wealth, judgment, evaluation, provider-control, runtime, persistence, API, or presentation meaning enters a governed field | Reject |

The codes are local review labels, not governed vocabulary, runtime
exceptions, public API values, or additions to Computation Outcome.

### 7.4 Normative validation vectors

Fixture identifiers below are illustrative values assumed to have been
issued by their proper owning authority. They do not mint production
identity.

#### 7.4.1 Single-Asset subject

Logical record:

```text
shape    = single_asset
asset_id = asset-a
role     = primary
```

Canonical bytes, grouped for readability:

```text
4D 53 42 31
01
00 00 00 07 61 73 73 65 74 2D 61
00 00 00 07 70 72 69 6D 61 72 79
```

Changing `asset-a` or `primary` changes identity. Replacing `asset-a` with a
ticker fails `SB-SUBJECT-003`.

#### 7.4.2 Multi-Asset ordering permutation

Both presentations:

```text
[(asset-b, quote), (asset-a, base)]
[(asset-a, base), (asset-b, quote)]
```

MUST resolve to:

```text
4D 53 42 31
02
00 00 00 02
00 00 00 07 61 73 73 65 74 2D 61
00 00 00 04 62 61 73 65
00 00 00 07 61 73 73 65 74 2D 62
00 00 00 05 71 75 6F 74 65
```

The two input orders therefore produce one Measure Subject identity.

#### 7.4.3 Market-context subject

Logical record:

```text
shape              = market_context
parameters.region  = GLOBAL
```

Canonical bytes:

```text
4D 53 42 31
03
00 00 00 01
00 00 00 06 72 65 67 69 6F 6E
00 00 00 06 47 4C 4F 42 41 4C
```

Adding any `asset_id` makes this record invalid.

#### 7.4.4 Manifest round trip

Using the §7.4.1 subject, one entry with requirement key `obs-min-1` and
canonical M39 identity reference `obs-001` serializes as:

```text
4F 49 4D 31
00 00 00 1B
  4D 53 42 31 01
  00 00 00 07 61 73 73 65 74 2D 61
  00 00 00 07 70 72 69 6D 61 72 79
00 00 00 01
00 00 00 09 6F 62 73 2D 6D 69 6E 2D 31
00 00 00 07 6F 62 73 2D 30 30 31
```

Decoding reconstructs exactly one subject and one Manifest Entry. Re-encoding
MUST reproduce the shown bytes.

#### 7.4.5 Manifest ordering permutation

Both presentations:

```text
[(obs-min-1, obs-002), (obs-min-1, obs-001)]
[(obs-min-1, obs-001), (obs-min-1, obs-002)]
```

MUST serialize entries in `obs-001`, then `obs-002` order and therefore
produce one manifest identity. This case is distinct from §7.4.2.

#### 7.4.6 M39 identity-equivalent representations

Two structurally different representations that M39 determines to denote the
same admitted Observation Event MUST yield the same canonical
`observation_identity` reference. For one requirement key they yield one
Manifest Entry, one canonical serialization, and one manifest identity.
Equal payload alone is insufficient to establish this result.

#### 7.4.7 Identity-distinct evidence conflict

Assume an applicable requirement permits exactly one Observation evidence
record. `obs-100` and `obs-101` are M39 identity-distinct and carry materially
incompatible frozen meanings for the same calculation-relevant coordinate.
Neither may be preferred silently. No resolved manifest exists for that
candidate set, and the consequence is the existing `INSUFFICIENT_INPUT`
outcome only.

#### 7.4.8 Exact-evidence reproduction

Given a Manifest Entry referencing `obs-001`, reconstruction MUST identify
the same admitted M39 Observation with unchanged identity, origin,
classification, payload meaning, temporal meaning, and relationships as
governed by M39. Any correction, merge, replacement, or supersession fails
`SB-MANIFEST-004`.

#### 7.4.9 One Observation cited by two requirement keys

Assume `obs-role-a` and `obs-role-b` are two distinct applicable
Observation-category Method Requirement keys and `obs-001` is one admitted
M39 Observation identity that supports both requirements. The manifest
contains exactly these two Manifest Entries:

```text
[
  (requirement_key = obs-role-a, observation_identity = obs-001),
  (requirement_key = obs-role-b, observation_identity = obs-001)
]
```

The mechanically relevant counts are:

```text
Manifest Entries                                  = 2
Distinct referenced M39 Observation identities   = {obs-001}
ObservationEvidenceCount                         = 1
```

The two distinct requirement roles create two Manifest Entries. They
reference one underlying admitted M39 Observation, so
`ObservationEvidenceCount` MUST equal exactly `1`, not `2`, under the
mandatory derivation in §5.4(7).

### 7.5 Validation matrix

| Required evidence | Covered by | Expected result |
| --- | --- | --- |
| Three Measure Subject shapes | §§7.4.1–7.4.3 | Valid canonical records |
| Subject ordering permutation | §7.4.2 | Same bytes and identity |
| Manifest entry-ordering permutation | §7.4.5 | Same bytes and identity |
| Subject byte round trip | §§7.4.1–7.4.3 | Exact reconstruction |
| Manifest byte round trip | §7.4.4 | Exact reconstruction |
| Provider-shaped identity rejection | §7.4.1 and `SB-SUBJECT-003` | Reject |
| M39 identity-equivalent representation | §7.4.6 | One entry and identity |
| Identity-distinct conflict | §7.4.7 | `INSUFFICIENT_INPUT` |
| Exact M39 evidence reproduction | §7.4.8 | Meaning unchanged |
| One Observation under two requirement keys | §7.4.9 | Two entries; `ObservationEvidenceCount = 1` |
| Field-level five-part gate | §6.2 | All pass |
| Negative-corpus exclusion | §§2.2, 4.8, 5.9, and 6 | No forbidden meaning |

These are documentation fixtures only. They authorize no executable test,
implementation, or runtime mechanism.

---

## 8. Compatibility Analysis

### 8.1 M34

This specification is compatible with:

- `M34-D-0004` because Asset classification and provider-reported evidence
  remain separately owned and are never inferred from a subject or manifest;
- `M34-D-0005` because no temporal claim, freshness claim, `latest`
  selection, or new degraded-state grammar is introduced; and
- `M34-D-0010` because descriptive market evidence remains separate from
  portfolio meaning, judgment, evaluation, execution, and presentation. No
  composite Instrument Analysis authority is created.

### 8.2 M39

This specification preserves the frozen M39 corpus:

- Manifest membership is limited to admitted M39 Observation evidence.
- M39 alone determines Observation Identity, identity equivalence,
  distinctness, and the immutable meaning of each referenced Observation.
- Equal values or semantically equivalent claims do not merge
  identity-distinct Observation Events.
- No Observation is created, corrected, reclassified, merged, superseded, or
  converted into a calculated result.
- Provider references, payload shapes, storage records, and runtime objects
  never become Observation identity.

### 8.3 M40

This specification preserves M40:

- Observation Input Manifest retains its exact frozen definition, sole owner,
  immutability, completeness, deterministic order, and M39-only membership.
- Market Measure and Calculated Market Measure remain descriptive,
  non-judgmental Market Intelligence concepts.
- The frozen four permitted input categories remain attributed to Market
  Measure Definition. Only their M39 Observation-evidence share enters the
  manifest.
- Computation Outcome is not redefined. Conflict uses only the existing
  `INSUFFICIENT_INPUT` meaning.
- Deterministic Calculation receives exact canonical inputs but is not
  implemented or otherwise re-specified here.

### 8.4 M41-WP1

This specification preserves M41-WP1:

- Measure Subject retains exactly its three confirmed shapes and owner.
- Market Measure Definition retains ownership of its declared subject-shape
  subset and permitted input-category declaration.
- Method Version retains its exact definition reference, semantic version,
  declared dependency versions, and Method Requirement set.
- Method Requirement retains its key, declaring Method Version,
  prerequisite category, closed evaluation grammar, and binary `MET` /
  `UNMET` result.
- `ObservationEvidenceCount` is the count of distinct referenced M39
  Observation identities in the entire invocation manifest. As derived in
  §5.4(7), Manifest Entry did not exist when M41-WP1 froze, so M41-WP1’s
  “M39 Observation evidence records” necessarily referred to the underlying
  admitted M39 Observation evidence rather than later-defined Manifest
  Entries; repeating one identity across requirement roles does not increase
  the count.
- Asset Definition Version remains a separately owned coordinate outside
  Measure Subject.
- No WP1 field is added, removed, renamed, reattributed, or reinterpreted.

### 8.5 Confirmed M41 Architecture and M41-WP2 Architecture

This specification fills only the two boxes and their binding relationship
assigned to WP2:

- Measure Subject receives record, identity, ordering, and serialization
  rules;
- Observation Input Manifest receives binding, identity, ordering,
  serialization, equivalence, and conflict rules;
- Manifest membership remains exact M39 evidence;
- the Subject and Manifest ordering-permutation cases remain distinct;
- evidence conflict fails closed using only an existing Computation Outcome;
  and
- WP3 Measurement Window work and WP4 Result / Provenance work remain
  untouched.

No architecture, ownership boundary, lifecycle, or implementation sequence
is changed.

---

## 9. Final Normative Summary

1. Measure Subject, Observation Input Manifest, and Manifest Entry are the
   only WP2-governed nouns specified here.
2. Market Intelligence solely owns all three. Asset Foundation solely owns
   each cited `asset_id`; frozen M39 remains authoritative for every cited
   Observation.
3. Measure Subject has exactly three mutually exclusive shapes:
   `single_asset`, `asset_set`, and `market_context`.
4. Measure Subject identity is exact canonical-byte identity under `MSB1`.
5. Multi-Asset subjects are ordered by `asset_id`, then role; market-context
   parameters are ordered by name, then value.
6. An Observation Input Manifest binds exactly one canonical Measure Subject
   and zero or more Manifest Entries.
7. Each Manifest Entry contains exactly one applicable Method Requirement key
   and one exact immutable frozen M39 Observation identity.
8. Manifest membership contains no Asset Foundation reference data,
   invocation parameter, or governed calculation dependency.
9. Manifest Entries are ordered by requirement key, then Observation
   identity, under the same unsigned-byte comparison discipline used for
   Measure Subject ordering.
10. Manifest identity is exact canonical-byte identity under `OIM1`.
11. M39 identity-equivalent representations collapse to one referenced
    Observation identity; identity-distinct Observations never collapse
    merely because their content is equal or similar.
12. A genuine unresolved evidence conflict permits no silent selection and
    maps only to existing `INSUFFICIENT_INPUT`.
13. Invalid shape, identity, cardinality, ordering, binding, serialization,
    ownership, or boundary content fails closed.
14. Every record is immutable once specified. Any identity-bearing change
    produces a different record.
15. This specification changes no architecture or frozen upstream contract
    and grants no implementation, runtime, production, provider,
    persistence, retrieval, or API authority.

**Implementation authority remains `NONE`. Runtime authority remains
`NONE`.**
