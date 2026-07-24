# M41-WP4 Stage B — Result, State, and Provenance Contract Specification

**Document role:** Normative contract specification

**Milestone:** M41 — Governed Market Measure Semantics

**Work package:** M41-WP4 — Result, State, and Provenance Model

**Stage:** B — Result, State, and Provenance Contract Specification

**Stage status:** `READY FOR INDEPENDENT REVIEW`

**M41 Architecture:** `COMPLETE`, `CONFIRMED`, `FROZEN`

**M41-WP1:** `COMPLETE`, `CONFIRMED`, `CLOSED`, `FROZEN`

**M41-WP2:** `COMPLETE`, `CONFIRMED`, `CLOSED`, `FROZEN`

**M41-WP3:** `COMPLETE`, `CONFIRMED`, `CLOSED`, `FROZEN`

**M41-WP4 Architecture:** `APPROVED`, `CONFIRMED`, `FROZEN`

**M41-WP4 Stage A:** `APPROVED`, `CONFIRMED`, `FROZEN`

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API authority:** `NONE`

**Production-method authority:** `NONE`

**Executable-validation authority:** `NONE`

---

## 0. Executive Determination

This specification closes the complete normative M41-WP4 Stage B allocation.
A conforming Market Measure Result is one immutable, owner-explicit record
that:

1. binds one exact Market Measure Definition, Method Version, Measure Subject,
   Observation Input Manifest, and Measurement Window;
2. carries exactly one of the four frozen Computation Outcome values;
3. carries a Measure Value if and only if that Outcome is `SUCCEEDED`;
4. binds the existing Canonical Temporal Claim with Event Type `Calculation`,
   Producing Domain `Market Intelligence`, one calculation-instant timestamp,
   and one of the six existing Degraded State values;
5. carries captured Provenance without redefining or recapturing it;
6. makes its complete WP1–WP3 lineage recoverable;
7. has one canonical full-record serialization and one distinct canonical
   identity-basis serialization;
8. derives Result identity as SHA-256 of the identity-basis octets;
9. excludes the calculation-instant timestamp and every other operational
   coordinate from identity while retaining the timestamp in the full
   serialization;
10. consumes the frozen WP3 handoff without repair, recomputation,
    re-rounding, or reclassification; and
11. permits partial-output composition only under the exact, disclosed rule in
    §11 and without a fifth Outcome or a new Degraded State.

No ambient default remains. No new governed vocabulary, Outcome, Degraded
State, Provenance meaning, Temporal Claim, Producing Domain, dependency
inventory, or owner is introduced.

---

## 1. Authority, Precedence, and Normative Language

### 1.1 Authority order

This specification is subordinate, in order, to:

1. the frozen platform and Asset Foundation architecture;
2. frozen M34 decisions and the frozen M39 and M40 corpora;
3. the frozen [M41 Architecture](M41_ARCHITECTURE_PROPOSAL.md);
4. frozen M41-WP1, including its
   [Definition, Method Version, and Applicability contract](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md);
5. frozen M41-WP2, including its
   [Subject and Manifest contract](M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md);
6. frozen M41-WP3, including its
   [Temporal, Unit, Adjustment, and Arithmetic contract](M41_WP3_STAGE_B_TEMPORAL_UNIT_ADJUSTMENT_ARITHMETIC_CONTRACT_SPECIFICATION.md)
   and [closeout](M41_WP3_CLOSEOUT.md);
7. the frozen
   [M41-WP4 Architecture](M41_WP4_ARCHITECTURE_PROPOSAL.md), as corrected by
   its [Required Corrections Response](M41_WP4_ARCHITECTURE_REQUIRED_CORRECTIONS_RESPONSE.md)
   and confirmed by its
   [Independent Architecture Confirmation](M41_WP4_ARCHITECTURE_INDEPENDENT_CONFIRMATION.md);
   and
8. the frozen
   [M41-WP4 Stage A register](M41_WP4_STAGE_A_VOCABULARY_AND_SEMANTIC_SURFACE_REGISTER.md)
   and its
   [Independent Confirmation](M41_WP4_STAGE_A_INDEPENDENT_CONFIRMATION.md).

If this specification conflicts with a higher authority, the higher authority
governs and the conflicting clause here is invalid. This specification cites
upstream authority; it does not summarize it into replacement authority.

### 1.2 Normative language

`MUST`, `MUST NOT`, `REQUIRED`, `SHALL`, `SHALL NOT`, `SHOULD`, `SHOULD NOT`,
and `MAY` are normative. Lowercase uses are explanatory.

The field names, encoding tokens, identity-basis labels, reason-representation
syntax, and validation labels in this document are ordinary contract language.
They are not governed vocabulary.

### 1.3 Explicit non-authority

This specification defines a semantic record and documentary conformance
rules only. It does not define or authorize:

- source code, a schema implementation, a serializer implementation, a hash
  implementation, a test runner, a conformance harness, or a reference
  implementation;
- runtime construction, clocks, retrieval, resolution, orchestration,
  fallback, retry, caching, or replay;
- provider selection, provider behavior, adapter behavior, or custody;
- persistence, database, indexing, retention, messaging, transport, API, SDK,
  endpoint, UI, or presentation behavior;
- a formula, concrete method, production catalog entry, registry, resolver,
  or computation kernel; or
- production adoption or executable validation.

---

## 2. Exact Upstream Consumption

### 2.1 WP1 — citation only

This specification consumes, without re-derivation:

| Frozen authority | Exact coordinate consumed | WP4 prohibition |
|---|---|---|
| [WP1 §5](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#5-market-measure-definition-contract) | Market Measure Definition identifier, revision, and required output-coordinate meaning | No Definition field, meaning, identity, or revision rule is added or reinterpreted. |
| [WP1 §6](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#6-method-version-contract) | Bound Definition reference, semantic version, and canonically ordered declared dependency-version list; together these are Method Version identity | No parallel dependency inventory, version rule, or identity rule is created. |
| [WP1 §7](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md#7-applicability-contract-method-requirement) | Method Requirement and Applicability meaning | No prerequisite is re-evaluated, relaxed, or reinterpreted. |
| [WP1 Candidate Register §6.6](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#66-measure-value) | Measure Value's exact confirmed meaning | No re-admission, untyped value, unit-unqualified value, new axis, or value on non-success. |

### 2.2 WP2 — citation only

This specification consumes, without re-derivation:

| Frozen authority | Exact coordinate consumed | WP4 prohibition |
|---|---|---|
| [WP2 Stage B §§3.1, 4](M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md#4-measure-subject-contract-specification) | One valid Measure Subject and its exact `MSB1` identity octets | No shape, field, identity, order, normalization, or serialization change. |
| [WP2 Stage B §§3.2–3.3, 5](M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md#5-observation-input-manifest-contract-specification) | One valid Observation Input Manifest and its exact `OIM1` identity octets; Manifest Entry's exact two-field structure | No evidence member, role, identity, order, or byte change. |
| [WP2 Stage B §5.4](M41_WP2_STAGE_B_SUBJECT_AND_MANIFEST_CONTRACT_SPECIFICATION.md#54-relationship-rules) | `ObservationEvidenceCount`, equal to the number of distinct referenced frozen M39 Observation identities | No counting reinterpretation. |

### 2.3 WP3 — citation only

This specification consumes, without re-derivation:

| Frozen authority | Exact coordinate consumed | WP4 prohibition |
|---|---|---|
| [WP3 Stage B §3](M41_WP3_STAGE_B_TEMPORAL_UNIT_ADJUSTMENT_ARITHMETIC_CONTRACT_SPECIFICATION.md#3-measurement-window-contract) | Measurement Window's exact canonical octets and identity | No reconstruction, repair, digest substitution, identity change, or substitution for the Result temporal claim. |
| [WP3 Stage B §§4–11](M41_WP3_STAGE_B_TEMPORAL_UNIT_ADJUSTMENT_ARITHMETIC_CONTRACT_SPECIFICATION.md#4-temporal-selection-cutoff-and-semantic-ordering) | Frozen deterministic temporal, unit, adjustment, arithmetic, dependency, and processing-order semantics | No semantic re-execution, default, alternate order, or re-rounding. |
| [WP3 Stage B §12](M41_WP3_STAGE_B_TEMPORAL_UNIT_ADJUSTMENT_ARITHMETIC_CONTRACT_SPECIFICATION.md#12-failure-classification) | Exactly one frozen Computation Outcome classification | No reclassification and no fifth Outcome. |
| [WP3 Stage B §14.6](M41_WP3_STAGE_B_TEMPORAL_UNIT_ADJUSTMENT_ARITHMETIC_CONTRACT_SPECIFICATION.md#146-wp4-handoff) and [WP3 closeout](M41_WP3_CLOSEOUT.md#deferred-responsibilities) | Exact Window octets/identity, semantic and dependency versions, qualified canonical arithmetic octets on success, or one frozen Outcome classification | No repair, recomputation, alternate path, or ownership transfer. |
| [WP3 Stage B §6.1](M41_WP3_STAGE_B_TEMPORAL_UNIT_ADJUSTMENT_ARITHMETIC_CONTRACT_SPECIFICATION.md#61-required-per-role-closure) and §12.1 | `independently_complete_coordinates` condition and deferral of Result composition | No rewrite of WP3 completeness or failure rules. |

The WP3 handoff is closed. Outcome-reason representation in §10 is a WP4
Result representation and does not add a fifth handoff coordinate.

---

## 3. Common Canonical Encoding

### 3.1 Canonical JSON subset

The full Result serialization and Result identity basis use this closed JSON
subset:

1. encoding is UTF-8 without a byte-order mark;
2. no whitespace occurs outside strings;
3. object member order is exactly the order specified in this document;
4. duplicate member names are prohibited;
5. strings MUST be Unicode Normalization Form C before UTF-8 encoding;
6. quotation mark, reverse solidus, and control characters use the shortest
   valid JSON escape; all other characters are encoded directly as UTF-8;
7. only objects, arrays, strings, and `null` occur;
8. JSON number and Boolean tokens do not occur;
9. arrays preserve the order fixed by this specification;
10. an unknown, additional, omitted, reordered, non-normalized, or
    non-canonically escaped member is non-canonical; and
11. no trailing octet is permitted.

Decode followed by encode MUST reproduce the input octets exactly. These rules
apply only to the WP4 wrapper. They do not alter or fork `MSB1`, `OIM1`, the
WP3 Measurement Window encoding, or WP3 numeric octets.

### 3.2 Imported octets

`hex:` followed by exactly two lowercase hexadecimal digits per octet, with no
separator, is the only WP4 wrapper for imported opaque octets.

- `subject_identity` decodes to the complete valid `MSB1` octet sequence.
- `manifest_identity` decodes to the complete valid `OIM1` octet sequence.
- `measurement_window_identity` decodes to the complete valid WP3 Measurement
  Window octet sequence.
- `captured_provenance` decodes to the exact finite non-empty Provenance
  material carried from its owner. For one referenced Observation identity,
  that carried octet sequence is immutable and exact; an alternate
  representation is not a second conforming carriage of the same captured
  Provenance. WP4 does not parse, normalize, enrich, or assign meaning to
  those octets.

A digest, surrogate identifier, storage key, provider identifier, or
presentation label MUST NOT replace imported identity octets.

### 3.3 Imported integers, versions, and timestamps

- Non-negative counts and revisions use WP3's canonical integer lexical form
  `I:<n>`.
- A Method Version semantic version retains WP1's exact `MAJOR.MINOR.PATCH`
  form.
- A Result calculation timestamp is exactly
  `YYYY-MM-DDThh:mm:ssZ`, with the validity and UTC-instant constraints of
  WP3 §3.1. Fractional seconds, numeric offsets, local times, `latest`, and an
  omitted timestamp are prohibited.
- Imported identifiers and versions retain their owning authority's canonical
  spelling and octets. WP4 performs no case folding, trimming, alias
  expansion, or identifier resolution.

---

## 4. Normative Market Measure Result Schema

### 4.1 Closed top-level record

A Market Measure Result contains exactly these members, in exactly this order:

| Order | Member | Cardinality | Requirement |
|---:|---|---:|---|
| 1 | `schema_version` | exactly 1 | Exact token `m41-wp4.market-measure-result/1`. |
| 2 | `result_identity` | exactly 1 | `sha256:` plus 64 lowercase hexadecimal digits, derived by §8. |
| 3 | `definition` | exactly 1 | Closed object in §4.2. |
| 4 | `method_version` | exactly 1 | Closed object in §4.3. |
| 5 | `subject_identity` | exactly 1 | Exact valid `MSB1` identity octets wrapped by §3.2. |
| 6 | `manifest_identity` | exactly 1 | Exact valid `OIM1` identity octets wrapped by §3.2. |
| 7 | `observation_evidence_count` | exactly 1 | Canonical non-negative integer equal to WP2 `ObservationEvidenceCount`. |
| 8 | `measurement_window_identity` | exactly 1 | Exact valid WP3 Measurement Window identity octets wrapped by §3.2. |
| 9 | `outcome` | exactly 1 | Exactly `SUCCEEDED`, `INSUFFICIENT_INPUT`, `DEPENDENCY_UNRESOLVED`, or `FAILED`. |
| 10 | `outcome_reasons` | exactly 1 array | Zero or more reason objects under §10; the array itself is mandatory. |
| 11 | `measure_value` | exactly 1 | A Measure Value object iff `SUCCEEDED`; otherwise JSON `null`. |
| 12 | `canonical_temporal_claim` | exactly 1 | Closed object in §4.4. |
| 13 | `provenance` | exactly 1 array | Zero or more carried-Provenance objects under §4.5. |

There are no extension members. Absence is never filled by a default.

### 4.2 `definition`

The object contains exactly, in order:

| Member | Cardinality | Requirement |
|---|---:|---|
| `identifier` | 1 | Exact WP1 Market Measure Definition identifier. |
| `revision` | 1 | Exact WP1 revision represented as a canonical positive integer. |
| `output_coordinate_meaning` | 1 | Exact frozen WP1 required output-coordinate meaning. |

The object is a citation of WP1 identity and meaning. It adds no Definition
field.

### 4.3 `method_version`

The object contains exactly, in order:

| Member | Cardinality | Requirement |
|---|---:|---|
| `definition_identifier` | 1 | Byte-identical to `definition.identifier`. |
| `definition_revision` | 1 | Byte-identical to `definition.revision`. |
| `semantic_version` | 1 | Exact WP1 semantic version. |
| `dependency_versions` | 1 array | Zero or more closed dependency objects, in WP1 ascending identifier code-point order. |

Each dependency object contains exactly `identifier`, then `version`, both
non-empty exact strings. No two entries may share an identifier. This object
is the complete WP1 Method Version identity coordinate; WP4 adds neither a
dependency nor a parallel version.

### 4.4 `canonical_temporal_claim`

The object contains exactly, in order:

| Member | Cardinality | Requirement |
|---|---:|---|
| `event_type` | 1 | Exact existing Event Type `Calculation`. |
| `producing_domain` | 1 | Exact existing Producing Domain `Market Intelligence`. |
| `authoritative_timestamp` | 1 | Exact calculation instant under §3.3. |
| `degraded_state` | 1 | Exactly one of `UNKNOWN`, `UNAVAILABLE`, `DELAYED`, `STALE`, `PARTIAL`, or `CONFLICTING`. |

This is the existing four-part Canonical Temporal Claim grammar. The
Measurement Window is an input-selection boundary and MUST NOT replace the
authoritative timestamp. Event Type `Snapshot Creation` is prohibited.
No Calculation Temporal Claim specialization and no specialized Producing
Domain exists.

The timestamp is mandatory in the full serialization and is part of carried
lineage. It does not participate in Result identity.

### 4.5 `provenance`

Each carried-Provenance object contains exactly, in order:

| Member | Cardinality | Requirement |
|---|---:|---|
| `observation_identity` | 1 | Exact frozen M39 Observation identity already present in the Manifest. |
| `captured_provenance` | 1 | Exact finite non-empty Provenance material wrapped as opaque octets under §3.2. |

The array:

1. MUST contain exactly one object for each distinct Observation identity in
   the Manifest;
2. MUST contain no identity absent from the Manifest;
3. MUST be ordered by the canonical Observation identity octets in unsigned
   byte order;
4. MUST have a length equal to `observation_evidence_count`; and
5. MUST be empty exactly when `observation_evidence_count` is `I:0`.

Connectivity & Ingestion retains ownership of Provenance meaning and capture.
Market Intelligence carries the exact material. WP4 does not parse it, infer
it, reconstruct it, enrich it, or create Provenance for interpolated,
normalized, adjusted, or otherwise derived working values.

### 4.6 Mandatory, optional, and conditional coordinates

All thirteen top-level members are mandatory.

The only optional-cardinality contents are:

- `method_version.dependency_versions` entries: zero or more;
- `outcome_reasons` entries: zero or more;
- `provenance` entries: zero or more, exactly constrained by §4.5; and
- a coordinate-set Measure Value's `coordinates`: one or more.

Conditional coordinates are:

- `measure_value` is an object iff `outcome` is `SUCCEEDED`; it is `null`
  otherwise;
- `declared_coordinate_keys` and `coordinates` occur only for the
  `coordinate_set` Measure Value form; and
- `coordinate_key` occurs only within a coordinate-set entry.

No unknown or implicitly defaulted coordinate is permitted.

### 4.7 Immutability

Every semantic coordinate is immutable. Changing any member produces either:

- a different Result identity when an identity-basis member changes; or
- a different full serialization of the same Result identity when only the
  calculation-instant timestamp changes.

Mutation in place is not a conforming interpretation.

---

## 5. Measure Value

### 5.1 Presence and exact WP3 carriage

A Measure Value is present if and only if `outcome` is `SUCCEEDED`.

Every canonical numeric lexical value MUST be the exact WP3 arithmetic handoff
octets interpreted as UTF-8, with no re-derivation, re-rounding, alternate
format, negative zero, NaN, or infinity. Type, unit, scale, basis, currency,
and output scale are the exact separately declared WP3 handoff coordinates.
Where a qualification is semantically inapplicable, the exact string
`not_applicable` MUST be carried; absence is prohibited.

Measure Value is not an Outcome, Degraded State, confidence, trust score,
quality judgment, or recommendation.

### 5.2 Scalar form

A scalar Measure Value contains exactly, in order:

| Member | Cardinality | Requirement |
|---|---:|---|
| `value_form` | 1 | Exact token `scalar`. |
| `value_type` | 1 | `integer`, `decimal`, or `rational`, matching the WP3 canonical lexical domain. |
| `canonical_value` | 1 | Exact WP3 canonical arithmetic string. |
| `unit` | 1 | Exact explicit unit qualification. |
| `scale` | 1 | Exact explicit scale qualification or `not_applicable`. |
| `basis` | 1 | Exact explicit basis qualification or `not_applicable`. |
| `currency` | 1 | Exact currency qualification or `not_applicable`. |
| `output_scale` | 1 | Exact canonical integer output scale or `not_applicable`. |

`value_type` MUST agree with the prefix of `canonical_value`: `integer` with
`I:`, `decimal` with `D:`, and `rational` with `R:`.

### 5.3 Coordinate-set form

A coordinate-set Measure Value contains exactly, in order:

| Member | Cardinality | Requirement |
|---|---:|---|
| `value_form` | 1 | Exact token `coordinate_set`. |
| `declared_coordinate_keys` | 1 array | Two or more unique non-empty coordinate keys in ascending UTF-8 unsigned-byte order. |
| `coordinates` | 1 array | One or more unique coordinate objects in ascending `coordinate_key` UTF-8 unsigned-byte order. |

Each coordinate object contains exactly, in order:

`coordinate_key`, `value_type`, `canonical_value`, `unit`, `scale`, `basis`,
`currency`, `output_scale`.

The seven value-qualification members obey §5.2. Every `coordinate_key` MUST
occur exactly once in `declared_coordinate_keys`. A placeholder, `null`,
unknown value, or omitted entry inside `coordinates` is prohibited.

If every declared key has one coordinate object, the value set is complete.
If `coordinates` is a proper non-empty subset of
`declared_coordinate_keys`, §11 governs partial composition.

---

## 6. Success and Non-Success Closure

### 6.1 Exactly-one Outcome

Each Result MUST carry exactly one, and only one, frozen Computation Outcome.
An array, combined token, omitted Outcome, duplicate Outcome, fifth Outcome,
or success-with-error hybrid is non-conforming.

The exact WP3 classification is copied into `outcome`. WP4 MUST NOT infer or
change it from a reason, Degraded State, value, timestamp, or provenance.

### 6.2 Normative Success Result

A Success Result:

- has `outcome:"SUCCEEDED"`;
- has exactly one conforming scalar or coordinate-set Measure Value object;
- carries zero or more conforming explanatory reason citations;
- carries exactly one valid Canonical Temporal Claim and complete lineage; and
- obeys the matrix in §7.

`SUCCEEDED` states only that the calculation completed with the value required
for that Result shape. It does not mean correct, trusted, current, suitable,
recommended, persisted, exposed, or operationally available.

### 6.3 Normative non-success Result

A non-success Result:

- has exactly one of `INSUFFICIENT_INPUT`, `DEPENDENCY_UNRESOLVED`, or
  `FAILED`;
- has `measure_value:null`;
- carries zero or more conforming explanatory reason citations;
- carries exactly one valid Canonical Temporal Claim and complete lineage; and
- obeys the matrix in §7.

No partial, stale, delayed, conflicting, or otherwise degraded qualification
can authorize a value on a non-success Result.

### 6.4 No-value-on-non-success

The following equivalence is normative:

```text
measure_value is an object  ⇔  outcome is SUCCEEDED
measure_value is null       ⇔  outcome is not SUCCEEDED
```

A non-success Result with any scalar, coordinate, placeholder, last-known
value, zero, NaN, infinity, or empty value set is non-conforming.
A `SUCCEEDED` Result with `null` is also non-conforming.

---

## 7. Outcome / Degraded State Interaction Matrix

Computation Outcome answers whether the specified calculation completed.
Degraded State qualifies whether the fact or Result is fully available as
ordinary current truth. Neither axis substitutes for or derives the other.

In the matrix, `V` means one conforming Measure Value object is mandatory and
`N` means `measure_value:null` is mandatory.

| Computation Outcome | `UNKNOWN` | `UNAVAILABLE` | `DELAYED` | `STALE` | `PARTIAL` | `CONFLICTING` |
|---|---|---|---|---|---|---|
| `SUCCEEDED` | Valid, `V` | Valid, `V` | Valid, `V` | Valid, `V` | Valid, `V`, only under §11 | Valid, `V` |
| `INSUFFICIENT_INPUT` | Valid, `N` | Valid, `N` | Valid, `N` | Valid, `N` | Valid, `N` | Valid, `N` |
| `DEPENDENCY_UNRESOLVED` | Valid, `N` | Valid, `N` | Valid, `N` | Valid, `N` | Valid, `N` | Valid, `N` |
| `FAILED` | Valid, `N` | Valid, `N` | Valid, `N` | Valid, `N` | Valid, `N` | Valid, `N` |

The 24 axis pairs are semantically orthogonal and therefore enumerated. The
exact Result shape remains conditional on the Outcome:

- a successful value is not removed merely because the Result is degraded;
- a non-success Result never gains a value merely because its Degraded State
  is `UNKNOWN`, `PARTIAL`, or any other approved state;
- `UNAVAILABLE` remains a Degraded State and is never an Outcome;
- `PARTIAL` on a non-success Result qualifies availability only and carries no
  partial value; and
- `SUCCEEDED` × `PARTIAL` is prohibited unless the coordinate-set value is a
  proper non-empty subset satisfying every §11 predicate. A scalar value, a
  complete coordinate set, an empty coordinate set, or an undisclosed subset
  in that cell is non-conforming.

Thus the matrix is total and deterministic without adding a state token.

---

## 8. Result Identity and Hash

### 8.1 Identity basis

The Result identity basis is a distinct canonical JSON object. It contains
exactly these members, in order:

1. `identity_schema`;
2. `definition`;
3. `method_version`;
4. `subject_identity`;
5. `manifest_identity`;
6. `observation_evidence_count`;
7. `measurement_window_identity`;
8. `outcome`;
9. `outcome_reasons`;
10. `measure_value`; and
11. `temporal_claim`.

`identity_schema` is the exact token
`m41-wp4.market-measure-result-identity/1`.

The first ten semantic members are byte-for-byte the corresponding full
Result members. `temporal_claim` contains exactly, in order:

1. `event_type`;
2. `producing_domain`; and
3. `degraded_state`.

These are byte-for-byte the corresponding members of
`canonical_temporal_claim`. The authoritative timestamp is omitted.

### 8.2 Identity exclusions

The identity basis excludes:

- `schema_version` and `result_identity` from the full wrapper;
- the Canonical Temporal Claim's calculation-instant timestamp;
- the opaque `provenance` array representation;
- host time, request time, retrieval time, receipt time, cache time, storage
  time, and display time;
- provider order, retrieval order, map-iteration order, custody, transport,
  cache state, storage location, process identity, thread identity, and
  randomness; and
- aliases, presentation labels, display formatting, locale, and host
  timezone.

The exclusions do not permit lineage omission. Subject, Manifest, evidence
count, Method Version identity and versions, Definition identity, Measurement
Window, Outcome, reasons, value, Event Type, Producing Domain, and Degraded
State all participate in identity.

### 8.3 Hash algorithm and identity form

`result_identity` is:

```text
"sha256:" + lowercase_hex(SHA-256(identity_basis_octets))
```

SHA-256 is the 256-bit algorithm specified by FIPS PUB 180-4, applied once to
the complete §8.1 UTF-8 octet sequence with no prefix, suffix, terminator,
salt, key, truncation, or alternate digest encoding. The hexadecimal suffix
has exactly 64 lowercase digits.

The hash algorithm is explicit contract syntax, not a governed semantic
dependency. A library name, library version, platform default, or storage
digest has no normative status.

### 8.4 Identity independence and sensitivity

Two full serializations with byte-identical identity bases MUST have identical
Result identities even if their calculation timestamps differ. Carried
Provenance is excluded from the identity basis because the exact Manifest
Observation identities already determine evidence identity; nevertheless,
§4.5 requires one immutable carried Provenance octet sequence per referenced
Observation identity, so alternate Provenance representations are not
conforming serializations of that lineage.

Changing any identity-basis octet changes the logical identity basis. It MUST
be rehashed; the stored `result_identity` MUST match. In particular, a change
to a dependency identifier or version changes Method Version identity and
therefore changes Result identity, even when the arithmetic value happens to
remain equal.

Hash equality is Result identity under this contract. It is not a correctness,
trust, quality, security, or collision-resistance claim beyond the exact
identity rule stated here.

---

## 9. Canonical Result Serialization and Round Trip

### 9.1 Full serialization

The canonical Result serialization is the §4.1 closed object encoded under
§3.1. It includes:

- the schema-version token;
- the derived Result identity;
- every frozen upstream identity and version;
- Outcome, reasons, and Measure Value or `null`;
- the complete Canonical Temporal Claim, including the calculation instant;
  and
- carried Provenance.

It is not the identity basis. The two byte views MUST NOT be conflated.

### 9.2 Schema-version semantics

`m41-wp4.market-measure-result/1` identifies exactly the full member set,
member order, lexical rules, cardinalities, and validation rules in this
document. `m41-wp4.market-measure-result-identity/1` identifies exactly the
identity-basis member set and order in §8.1.

A change that alters parsing, member order, permitted lexical forms,
cardinality, identity participation, or semantic interpretation requires a
new explicit version token. An unknown version is rejected. A reader MUST NOT
infer compatibility, insert defaults, ignore unknown members, or convert one
version into another.

The identity-schema token participates in identity. The full schema token does
not because it is replaced by the identity-schema token in the identity view.

### 9.3 Deterministic round trip

For every valid full serialization:

1. decoding under §3 reconstructs exactly one logical Result;
2. validation under §§4–13 succeeds;
3. reconstructing the §8 identity basis and applying SHA-256 reproduces the
   carried `result_identity`; and
4. re-encoding the logical Result reproduces every original octet.

For every valid logical Result, encoding produces exactly one full
serialization. No external registry order, locale, clock, provider,
configuration, or mutable state is needed to parse or re-encode it.

---

## 10. Outcome Reason Representation

### 10.1 Purpose and optionality

A reason explains an already-fixed Outcome. It does not classify, override,
weaken, strengthen, or add an Outcome; create a verdict; or introduce
judgment, evaluation, authorization, or action meaning.

The `outcome_reasons` array is mandatory. It MAY be empty for any Outcome
because the exact WP3 handoff contains a classification, not a fifth
reason-coordinate handoff. If reasons are carried, each MUST be an exact
normative-predicate citation under this section.

### 10.2 Closed reason object

Each reason object contains exactly, in order:

| Member | Cardinality | Requirement |
|---|---:|---|
| `authority` | 1 | Exact immutable identifier of the frozen authority containing the predicate. |
| `section` | 1 | Exact section number or stable anchor within that authority. |
| `predicate` | 1 | Exact one-based table-row, list-item, or clause ordinal, written as ASCII digits without leading zero. |
| `coordinate` | 1 | Exact JSON Pointer into the WP4 Result, or exact token `none` when no Result coordinate is the predicate's subject. |

This is a citation representation, not a reason-code taxonomy. Free text,
provider codes, exception names, stack traces, runtime messages, localized
text, inferred causes, quality scores, and recommendation language are
prohibited.

### 10.3 Ordering and consistency

Reason objects MUST be sorted by the UTF-8 octets of `authority`, then
`section`, then `predicate`, then `coordinate`, all in unsigned byte order.
Duplicate objects are prohibited.

Every cited predicate MUST:

1. exist in frozen authority;
2. apply to the exact Result coordinates;
3. map to the carried Outcome under frozen WP3 §12.1; and
4. require no WP4 recomputation or reclassification.

Reasons participate in the identity basis. The same logical reason set
therefore has one order and one Result identity.

---

## 11. Partial-Output / Partial-Result Composition

### 11.1 Preconditions

Partial composition is permitted only when all of the following are true:

1. the exact frozen Definition output meaning permits a value set;
2. the exact bound Method Version semantics enumerate two or more separable
   output coordinate keys;
3. WP3 §6.1 applies the exact `independently_complete_coordinates` treatment;
4. at least one, but not all, declared coordinates has complete qualified
   canonical arithmetic octets;
5. every carried coordinate is independently complete under the exact frozen
   semantics; and
6. the WP3 handoff classifies the composed Result `SUCCEEDED` for those
   independently resultable coordinates.

No WP4 inference may satisfy a precondition. In the absence of every explicit
precondition, partial composition is prohibited.

### 11.2 Normative partial shape

A permitted partial Result:

- has `outcome:"SUCCEEDED"`;
- has `canonical_temporal_claim.degraded_state:"PARTIAL"`;
- has a `coordinate_set` Measure Value;
- lists the complete exact declared set in `declared_coordinate_keys`;
- carries only the proper non-empty subset of independently complete
  coordinates in `coordinates`;
- carries no placeholder for an incomplete coordinate; and
- includes both the declared-key list and carried coordinates in its identity
  basis.

This shape discloses both successful completion of the carried coordinates and
partial availability of the declared value set. It does not create
“partially succeeded,” a fifth Outcome, a seventh Degraded State, or a third
classification axis.

### 11.3 Prohibited partial shapes

The following are non-conforming:

- a scalar Measure Value with Degraded State `PARTIAL`;
- a proper coordinate subset with a Degraded State other than `PARTIAL`;
- `PARTIAL` with a complete coordinate set;
- an empty `coordinates` array;
- a placeholder, `null`, zero-fill, last-known value, or invented value for an
  incomplete coordinate;
- a coordinate key absent from the exact declared set;
- a subset inferred from missing data without explicit Definition and Method
  Version permission;
- any Measure Value on a non-success Outcome; or
- an omitted declared-key list that makes a subset appear to be a complete
  Result.

For any non-success Outcome, §6.4 governs: independently complete working
coordinates are not exposed as a Measure Value. `PARTIAL` may qualify that
non-success Result's availability, but the Result remains explicitly
non-success and value-free.

---

## 12. Lineage Completeness and WP3 Handoff

### 12.1 Complete lineage predicate

A Result has complete lineage only when all of the following are recoverable
from its full serialization without an ambient lookup:

- exact Market Measure Definition identifier, revision, and output-coordinate
  meaning;
- exact Method Version identity: bound Definition, semantic version, and
  ordered dependency-version list;
- exact Measure Subject `MSB1` identity octets;
- exact Observation Input Manifest `OIM1` identity octets;
- exact `ObservationEvidenceCount`;
- exact Measurement Window identity octets;
- exact Outcome, reasons, and Measure Value when permitted;
- the complete Canonical Temporal Claim, including calculation instant and
  Degraded State; and
- exact carried Provenance material for every distinct Manifest Observation
  identity.

The embedded Manifest MUST decode to the same Subject octets carried by
`subject_identity`. The embedded Measurement Window MUST decode to the same
Manifest octets carried by `manifest_identity`. The evidence count and
Provenance cardinality MUST equal the distinct Observation identity count
derived under WP2.

### 12.2 Non-laundering

Only identities already present in the exact Manifest may appear as witnessed
Observation lineage. An interpolated, normalized, converted, adjusted,
quantized, aggregated, or otherwise derived working value:

- is not an Observation;
- receives no Observation identity;
- receives no captured-Provenance entry;
- is not inserted into or used to modify the Manifest; and
- may appear only as exact WP3 arithmetic output inside a permitted Measure
  Value.

### 12.3 Exact handoff consumption

WP4 consumes exactly:

1. Measurement Window octets/identity;
2. exact semantic and dependency versions;
3. exact qualified canonical arithmetic octets on success; or
4. one frozen non-success Outcome classification.

The Result MUST reject a handoff if any carried octet or version differs from
the supplied frozen coordinate. WP4 MUST NOT repair, normalize, round,
recalculate, retry, choose an alternate dependency, fill an omitted
coordinate, or select a different Outcome.

---

## 13. Validation and Error Rules

Validation is fail-closed and documentary. A failed rule means the proposed
record is not a conforming Market Measure Result; it does not create a new
Computation Outcome or runtime exception contract.

### 13.1 Structural validation

A proposed Result is non-conforming if:

- a required member is absent, duplicated, additional, reordered, or has the
  wrong cardinality;
- a string, escape, integer, version, timestamp, hexadecimal wrapper, array
  order, or imported octet sequence is non-canonical;
- `schema_version` is unknown;
- an embedded `MSB1`, `OIM1`, or Measurement Window fails its owning frozen
  contract;
- a Definition/Method binding, Subject/Manifest binding, or Window/Manifest
  binding disagrees;
- a dependency list is unordered, duplicated, ambient, ranged, or versionless;
  or
- `result_identity` does not equal the §8 recomputation.

### 13.2 Outcome and value validation

A proposed Result is non-conforming if:

- Outcome is absent, repeated, combined, or outside the four frozen values;
- `SUCCEEDED` has `measure_value:null`;
- a non-success Outcome has any Measure Value;
- Measure Value type and canonical numeric prefix disagree;
- any value is untyped, unit-unqualified, re-rounded, non-canonical, NaN,
  infinity, or negative zero;
- a reason citation contradicts the Outcome or cites no frozen predicate; or
- the Outcome/Degraded State shape violates §7 or §11.

### 13.3 Temporal, provenance, and lineage validation

A proposed Result is non-conforming if:

- Event Type is not `Calculation`, including `Snapshot Creation`;
- Producing Domain is not `Market Intelligence`;
- the timestamp is absent, non-UTC, non-canonical, or substituted by the
  Measurement Window;
- Degraded State is outside the six frozen values;
- a Provenance identity is absent from the Manifest, missing from the
  Provenance array, duplicated, or out of order;
- Provenance cardinality disagrees with `ObservationEvidenceCount`;
- derived working material is represented as witnessed evidence; or
- any required lineage coordinate is not exactly recoverable.

### 13.4 Identity, serialization, hash, and round-trip validation

A proposed Result is non-conforming if:

- the identity basis contains the calculation timestamp, Provenance wrapper,
  or another excluded operational coordinate;
- the identity basis omits an included semantic coordinate;
- a different identity-basis member order is used;
- a digest algorithm, salt, key, truncation, case, or prefix differs from §8;
- decode followed by encode changes any octet; or
- two encodings are accepted for one logical Result.

---

## 14. Field-Level Five-Part Ownership-Boundary Gate

| Field or rule group | Permitted subject | Permitted inputs | Descriptive output meaning | Prohibited domain inputs excluded | Judgment/evaluation excluded | Result |
|---|---|---|---|---|---|---|
| Definition and Method Version coordinates | Exact WP1 calculation specification | Frozen WP1 identity and versions | Exact calculation-specification lineage | Ledger, Portfolio, Workspace, Wealth, person, goal, and transaction state excluded | No correctness, trust, ranking, or recommendation | Pass |
| Subject and Manifest identities/count | Exact WP2 Measure Subject and evidence binding | Exact `MSB1`, `OIM1`, and distinct Observation identities | Exact subject/evidence lineage | Same exclusions; no membership inference | No source preference or evidence verdict | Pass |
| Measurement Window identity | Exact WP3 input-selection boundary | Exact WP3 Window octets | Deterministic calculation boundary | Same exclusions; no ambient current time | No recency preference or quality judgment | Pass |
| Outcome and reasons | Exact calculation invocation | Exact WP3 classification and frozen-predicate citations | Completion/non-completion plus explanation | Same exclusions; no runtime error state | No fifth verdict, confidence, or action meaning | Pass |
| Measure Value | Exact Result subject | Exact qualified WP3 arithmetic octets | Typed, unit-qualified calculated value on success | Same exclusions; no portfolio or ledger value | No correctness, trust, or recommendation | Pass |
| Canonical Temporal Claim / matrix | Exact calculated Result | Existing Event Type, Producing Domain, timestamp, and Degraded State | Calculation time and availability qualification | Same exclusions; no cache/display clock | No freshness judgment beyond frozen state meaning | Pass |
| Provenance carriage / lineage | Exact Manifest evidence and Result coordinates | Captured Provenance plus exact WP1–WP3 identities | Attribution and recoverability | Same exclusions; no new custody meaning | No source ranking or truth verdict | Pass |
| Identity / serialization / hash | Exact immutable Result | Explicit semantic coordinates and fixed syntax | Deterministic Result identity and octets | Same exclusions; all operational state excluded | Hash is not trust or correctness | Pass |
| Partial composition | Exact separable value-set Result | Explicit Definition/Method permission and WP3 complete coordinates | Disclosed partial availability of independently complete values | Same exclusions; no inferred missing values | No best-effort or quality threshold | Pass |

Every row passes. Carriage is not capture; composition is not ownership
transfer; serialization is not semantic ownership; validation is not authority
to redefine.

---

## 15. Normative Golden Vectors

### 15.1 Status and conventions

These Golden Vectors are normative documentation only. They are not executable
fixtures, code, a test runner, a reference implementation, or production
admission. All named Definitions, Method Versions, Assets, dependencies, and
values are illustrative and non-production.

Unless a vector overrides a coordinate, it uses the common bundle below.
Every one-line JSON span denotes its exact UTF-8 octets with no trailing
newline.

### 15.2 Common upstream bundle

The illustrative `single_asset` Subject has:

```text
MSB1 hex = 4d534231010000000d61737365743a6578616d706c65000000077072696d617279
```

It decodes under WP2 to `asset_id="asset:example"`, `role="primary"`.
The empty-evidence Manifest has:

```text
OIM1 hex = 4f494d31000000214d534231010000000d61737365743a6578616d706c65000000077072696d61727900000000
```

`ObservationEvidenceCount` is `I:0`; Provenance is therefore `[]`.

The exact Measurement Window octets are:

```json
{"schema_version":"m41-wp3.measurement-window/1","window_kind":"elapsed","manifest_identity":"hex:4f494d31000000214d534231010000000d61737365743a6578616d706c65000000077072696d61727900000000","start":{"precision":"instant","value":"2025-01-01T00:00:00Z","disambiguation":"not_applicable"},"start_edge":"inclusive","cutoff":{"precision":"instant","value":"2025-01-02T00:00:00Z","disambiguation":"not_applicable"},"cutoff_edge":"inclusive","time_basis":"elapsed","timezone_ref":{"kind":"utc","identifier":"UTC","version":"fixed"},"calendar_ref":{"kind":"none","identifier":"none","version":"none"},"count":"I:0"}
```

The common Definition is identifier
`market-measure-definition:vector-price`, revision `I:1`, output-coordinate
meaning `Identity`. The common Method Version binds that Definition, has
semantic version `1.0.0`, and has an empty dependency-version list.

### 15.3 GV-B-01 — complete Success Result, serialization, and hash

The WP3 success handoff value is:

```json
{"value_form":"scalar","value_type":"decimal","canonical_value":"D:125E-2","unit":"unit:usd_per_unit","scale":"D:1E0","basis":"raw","currency":"USD","output_scale":"I:2"}
```

The exact identity basis is:

```json
{"identity_schema":"m41-wp4.market-measure-result-identity/1","definition":{"identifier":"market-measure-definition:vector-price","revision":"I:1","output_coordinate_meaning":"Identity"},"method_version":{"definition_identifier":"market-measure-definition:vector-price","definition_revision":"I:1","semantic_version":"1.0.0","dependency_versions":[]},"subject_identity":"hex:4d534231010000000d61737365743a6578616d706c65000000077072696d617279","manifest_identity":"hex:4f494d31000000214d534231010000000d61737365743a6578616d706c65000000077072696d61727900000000","observation_evidence_count":"I:0","measurement_window_identity":"hex:7b22736368656d615f76657273696f6e223a226d34312d7770332e6d6561737572656d656e742d77696e646f772f31222c2277696e646f775f6b696e64223a22656c6170736564222c226d616e69666573745f6964656e74697479223a226865783a346634393464333130303030303032313464353334323331303130303030303030643631373337333635373433613635373836313664373036633635303030303030303737303732363936643631373237393030303030303030222c227374617274223a7b22707265636973696f6e223a22696e7374616e74222c2276616c7565223a22323032352d30312d30315430303a30303a30305a222c22646973616d626967756174696f6e223a226e6f745f6170706c696361626c65227d2c2273746172745f65646765223a22696e636c7573697665222c226375746f6666223a7b22707265636973696f6e223a22696e7374616e74222c2276616c7565223a22323032352d30312d30325430303a30303a30305a222c22646973616d626967756174696f6e223a226e6f745f6170706c696361626c65227d2c226375746f66665f65646765223a22696e636c7573697665222c2274696d655f6261736973223a22656c6170736564222c2274696d657a6f6e655f726566223a7b226b696e64223a22757463222c226964656e746966696572223a22555443222c2276657273696f6e223a226669786564227d2c2263616c656e6461725f726566223a7b226b696e64223a226e6f6e65222c226964656e746966696572223a226e6f6e65222c2276657273696f6e223a226e6f6e65227d2c22636f756e74223a22493a30227d","outcome":"SUCCEEDED","outcome_reasons":[],"measure_value":{"value_form":"scalar","value_type":"decimal","canonical_value":"D:125E-2","unit":"unit:usd_per_unit","scale":"D:1E0","basis":"raw","currency":"USD","output_scale":"I:2"},"temporal_claim":{"event_type":"Calculation","producing_domain":"Market Intelligence","degraded_state":"UNKNOWN"}}
```

Expected Result identity:

```text
sha256:f15e394c19d9da93114314e5549a97deffbd4794f253655b0d18ce39880c7515
```

The exact full serialization is:

```json
{"schema_version":"m41-wp4.market-measure-result/1","result_identity":"sha256:f15e394c19d9da93114314e5549a97deffbd4794f253655b0d18ce39880c7515","definition":{"identifier":"market-measure-definition:vector-price","revision":"I:1","output_coordinate_meaning":"Identity"},"method_version":{"definition_identifier":"market-measure-definition:vector-price","definition_revision":"I:1","semantic_version":"1.0.0","dependency_versions":[]},"subject_identity":"hex:4d534231010000000d61737365743a6578616d706c65000000077072696d617279","manifest_identity":"hex:4f494d31000000214d534231010000000d61737365743a6578616d706c65000000077072696d61727900000000","observation_evidence_count":"I:0","measurement_window_identity":"hex:7b22736368656d615f76657273696f6e223a226d34312d7770332e6d6561737572656d656e742d77696e646f772f31222c2277696e646f775f6b696e64223a22656c6170736564222c226d616e69666573745f6964656e74697479223a226865783a346634393464333130303030303032313464353334323331303130303030303030643631373337333635373433613635373836313664373036633635303030303030303737303732363936643631373237393030303030303030222c227374617274223a7b22707265636973696f6e223a22696e7374616e74222c2276616c7565223a22323032352d30312d30315430303a30303a30305a222c22646973616d626967756174696f6e223a226e6f745f6170706c696361626c65227d2c2273746172745f65646765223a22696e636c7573697665222c226375746f6666223a7b22707265636973696f6e223a22696e7374616e74222c2276616c7565223a22323032352d30312d30325430303a30303a30305a222c22646973616d626967756174696f6e223a226e6f745f6170706c696361626c65227d2c226375746f66665f65646765223a22696e636c7573697665222c2274696d655f6261736973223a22656c6170736564222c2274696d657a6f6e655f726566223a7b226b696e64223a22757463222c226964656e746966696572223a22555443222c2276657273696f6e223a226669786564227d2c2263616c656e6461725f726566223a7b226b696e64223a226e6f6e65222c226964656e746966696572223a226e6f6e65222c2276657273696f6e223a226e6f6e65227d2c22636f756e74223a22493a30227d","outcome":"SUCCEEDED","outcome_reasons":[],"measure_value":{"value_form":"scalar","value_type":"decimal","canonical_value":"D:125E-2","unit":"unit:usd_per_unit","scale":"D:1E0","basis":"raw","currency":"USD","output_scale":"I:2"},"canonical_temporal_claim":{"event_type":"Calculation","producing_domain":"Market Intelligence","authoritative_timestamp":"2025-01-02T00:00:01Z","degraded_state":"UNKNOWN"},"provenance":[]}
```

SHA-256 of the full serialization, for round-trip octet comparison only, is:

```text
sha256:9c06e7025684d445efb1d744e442ecad281ef217711c1688581033aa74fa6cfd
```

This full-serialization digest is not Result identity.

### 15.4 GV-B-02 through GV-B-04 — non-success closure

Each row uses the common bundle, `degraded_state:"UNKNOWN"`, and
`measure_value:null`.

| Vector | Outcome | Exact reason object | Expected Result identity |
|---|---|---|---|
| GV-B-02 | `INSUFFICIENT_INPUT` | `{"authority":"M41_WP3_STAGE_B_TEMPORAL_UNIT_ADJUSTMENT_ARITHMETIC_CONTRACT_SPECIFICATION.md","section":"3.3","predicate":"1","coordinate":"/measurement_window_identity"}` | `sha256:0ea5d6b95777178d190b103e33809a48bfd30de0446ee7248d65f657988dbf6e` |
| GV-B-03 | `DEPENDENCY_UNRESOLVED` | `{"authority":"M41_WP3_STAGE_B_TEMPORAL_UNIT_ADJUSTMENT_ARITHMETIC_CONTRACT_SPECIFICATION.md","section":"10.2","predicate":"1","coordinate":"/method_version/dependency_versions"}` | `sha256:d91e2a96389035ec31ea108e079595fca9bfd38512da9f7510e8417b11f904ed` |
| GV-B-04 | `FAILED` | `{"authority":"M41_WP3_STAGE_B_TEMPORAL_UNIT_ADJUSTMENT_ARITHMETIC_CONTRACT_SPECIFICATION.md","section":"9.2","predicate":"1","coordinate":"/measure_value"}` | `sha256:f5def90fefbf33dd9781fa7be2a3246902491ec04f115fe9f5661b31fd569258` |

Each identity is SHA-256 of the §8.1 basis formed by replacing GV-B-01's
Outcome, one-element `outcome_reasons` array, and Measure Value exactly as
shown. Adding any value to any row is rejection. Replacing `null` with an empty
object or empty set is also rejection.

### 15.5 GV-B-05 — present-if-and-only-if closure

| Input shape | Expected determination |
|---|---|
| `SUCCEEDED` plus the GV-B-01 Measure Value | Conforming |
| `SUCCEEDED` plus `null` | Reject |
| `INSUFFICIENT_INPUT` plus `null` | Conforming |
| `DEPENDENCY_UNRESOLVED` plus `null` | Conforming |
| `FAILED` plus `null` | Conforming |
| Any non-success Outcome plus any scalar, set, placeholder, zero, NaN, or last-known value | Reject |

This proves both directions of §6.4.

### 15.6 GV-B-06 — calculation timestamp identity independence

Start with GV-B-01. Change only:

```text
authoritative_timestamp: 2025-01-02T00:00:01Z
                      → 2025-01-02T00:00:02Z
```

Expected:

- full serialization octets differ;
- round-trip preserves the changed timestamp;
- identity basis octets remain identical; and
- Result identity remains
  `sha256:f15e394c19d9da93114314e5549a97deffbd4794f253655b0d18ce39880c7515`.

The same expected identity holds when only host time, request time, retrieval
time, provider order, cache state, storage location, or presentation labels
differ, because none is a Result coordinate or identity input.

### 15.7 GV-B-07 — dependency-version sensitivity

Start with GV-B-01 and replace the empty dependency list with:

```json
[{"identifier":"dep:calendar","version":"2025a"}]
```

All other identity-basis members remain unchanged. Expected Result identity:

```text
sha256:696e71b0523e50ee9ae407240005f0c97e736ec3dd0275e9decbc7d634f90967
```

The changed dependency changes Method Version identity and Result identity.
Equal arithmetic output does not preserve the old identity.

### 15.8 GV-B-08 — hash stability

Two independent documentary derivations from the exact GV-B-01 logical
coordinates MUST produce the exact GV-B-01 identity-basis line and:

```text
sha256:f15e394c19d9da93114314e5549a97deffbd4794f253655b0d18ce39880c7515
```

Uppercase hexadecimal, SHA-512, a hash of the full Result, a hash of pretty
printed JSON, a hash including the timestamp, or a hash of decoded upstream
objects is rejection.

### 15.9 GV-B-09 — deterministic round trip

Given only GV-B-01's exact full serialization and §§3–9:

1. decode all thirteen members;
2. reconstruct the exact logical Result;
3. derive and verify the exact Result identity;
4. re-encode; and
5. compare SHA-256 of the full octets.

Expected full-octet digest:

```text
sha256:9c06e7025684d445efb1d744e442ecad281ef217711c1688581033aa74fa6cfd
```

Any octet change is rejection, including member reordering or a trailing
newline.

### 15.10 GV-B-10 — complete lineage

GV-B-01 MUST yield, without an ambient lookup:

| Lineage coordinate | Expected value |
|---|---|
| Definition | `market-measure-definition:vector-price`, `I:1`, `Identity` |
| Method Version | same bound Definition, `1.0.0`, `[]` dependencies |
| Subject | exact `MSB1` hex from §15.2 |
| Manifest | exact `OIM1` hex from §15.2 |
| ObservationEvidenceCount | `I:0` |
| Measurement Window | exact §15.2 Window octets |
| Outcome/value | `SUCCEEDED`; exact `D:125E-2` qualification bundle |
| Canonical Temporal Claim | `Calculation`; `Market Intelligence`; `2025-01-02T00:00:01Z`; `UNKNOWN` |
| Provenance | `[]`, exactly because evidence count is zero |

If any coordinate is unavailable, substituted by a digest, or inconsistent
with its embedded upstream binding, reject.

### 15.11 GV-B-11 — temporal binding and reserved exclusion

| Variant | Expected determination |
|---|---|
| GV-B-01 `Calculation` / `Market Intelligence` | Conforming |
| Replace Event Type with `Snapshot Creation` | Reject |
| Replace Event Type with `Observation` | Reject |
| Replace Producing Domain with any specialization | Reject |
| Omit authoritative timestamp | Reject |
| Use Window cutoff as the authoritative timestamp without an independently established calculation instant | Reject |
| Add a `calculation_temporal_claim` member | Reject |

### 15.12 GV-B-12 — total Outcome / Degraded State matrix

For each of the 24 §7 cells:

- use GV-B-01's value for each `SUCCEEDED` row except `PARTIAL`;
- use `null` for every non-success row;
- substitute the column's exact Degraded State; and
- recompute identity because Degraded State participates in the basis.

Expected shape matrix:

| Outcome | `UNKNOWN` | `UNAVAILABLE` | `DELAYED` | `STALE` | `PARTIAL` | `CONFLICTING` |
|---|---:|---:|---:|---:|---:|---:|
| `SUCCEEDED` | V | V | V | V | P | V |
| `INSUFFICIENT_INPUT` | N | N | N | N | N | N |
| `DEPENDENCY_UNRESOLVED` | N | N | N | N | N | N |
| `FAILED` | N | N | N | N | N | N |

`V` is the full scalar success shape, `N` is `null`, and `P` is the exact
partial coordinate-set shape in GV-B-15. `SUCCEEDED` × `PARTIAL` with the
scalar GV-B-01 value is rejected. Every non-success cell with a value is
rejected. No cell changes the carried Outcome.

### 15.13 GV-B-13 — Provenance carriage and non-laundering

For a separate documentary Manifest with one distinct Observation identity
`obs:vector:1`, set:

```json
"observation_evidence_count":"I:1"
```

and:

```json
"provenance":[{"observation_identity":"obs:vector:1","captured_provenance":"hex:736f757263652d74696d652d61646170746572"}]
```

Expected: conforming only when the exact Manifest contains
`obs:vector:1` and its WP2 distinct-identity count is one. The opaque bytes
decode to the carried material and are not interpreted by WP4.

Reject:

- empty Provenance;
- a second entry for the same identity;
- an identity absent from the Manifest;
- a count other than `I:1`;
- provider or value equality substituted for Observation identity; or
- a synthetic Provenance entry for an interpolated, normalized, adjusted, or
  quantized working value.

### 15.14 GV-B-14 — exact WP3 handoff

Input: the common Window, semantic version `1.0.0`, empty dependency list, and
the exact qualified `D:125E-2` handoff.

Expected: GV-B-01 carries every octet unchanged.

Reject each independent mutation:

- `D:1250E-3` in place of canonical `D:125E-2`;
- a re-rounded value;
- decoded-and-re-serialized Window octets differing from the handoff;
- a dependency added or removed;
- a repaired invalid Window;
- `SUCCEEDED` substituted for a handed-off non-success Outcome; or
- a retry/alternate path used to obtain a different Result.

### 15.15 GV-B-15 — permitted partial composition

Assume, for this non-production vector only, that every §11.1 precondition is
explicitly satisfied for declared coordinate keys `close` and `open`, and WP3
hands off only the independently complete `close` coordinate.

The exact Measure Value is:

```json
{"value_form":"coordinate_set","declared_coordinate_keys":["close","open"],"coordinates":[{"coordinate_key":"close","value_type":"decimal","canonical_value":"D:125E-2","unit":"unit:usd_per_unit","scale":"D:1E0","basis":"raw","currency":"USD","output_scale":"I:2"}]}
```

Outcome is `SUCCEEDED`; Degraded State is `PARTIAL`; reasons are empty.
With the common bundle, expected Result identity is:

```text
sha256:b3ce70de3d87715cc47037c7d2404ee4db8f015b1af5e92caada008a5cd3c3e6
```

The missing `open` coordinate has no placeholder. The declared-key list makes
the partial composition explicit.

### 15.16 GV-B-16 — prohibited partial variants

Starting from GV-B-15:

| Mutation | Expected determination |
|---|---|
| Change Degraded State to `UNKNOWN` | Reject: subset is undisclosed. |
| Remove `declared_coordinate_keys` | Reject: subset can masquerade as complete. |
| Add `open:null` | Reject: placeholder. |
| Add invented `open` value | Reject: not a WP3 handoff coordinate. |
| Use scalar value with `PARTIAL` | Reject. |
| Carry both `close` and `open` while retaining `PARTIAL` | Reject: set is complete. |
| Keep value but change Outcome to `FAILED` | Reject: no value on non-success. |
| Remove explicit independent-completion permission | Reject. |
| Use an empty `coordinates` array | Reject. |

### 15.17 GV-B-17 — deterministic outcome-reason representation

The one-element reason array:

```json
[{"authority":"M41_WP3_STAGE_B_TEMPORAL_UNIT_ADJUSTMENT_ARITHMETIC_CONTRACT_SPECIFICATION.md","section":"3.3","predicate":"1","coordinate":"/measurement_window_identity"}]
```

is canonical for GV-B-02. The same logical citation with reordered object
members, localized prose, a runtime exception string, or a leading-zero
predicate `"01"` is rejected.

Two reasons supplied in reverse canonical tuple order MUST be rejected, not
silently accepted as a second serialization. A reason mapping to a different
Outcome is rejected. Removing all reasons is structurally permitted, but it
changes the identity basis and therefore requires a different Result identity.

### 15.18 GV-B-18 — schema-version and Unicode determinism

| Mutation | Expected determination |
|---|---|
| Unknown full schema token | Reject |
| Unknown identity-schema token | Reject |
| Omitted schema token | Reject |
| Additional member | Reject |
| Same visible string encoded in non-NFC form | Reject |
| Byte-order mark, insignificant whitespace, or trailing newline | Reject |
| Same dependency entries in non-canonical order | Reject |

No compatibility or normalization default repairs these cases.

---

## 16. Negative Corpus

This specification explicitly prohibits:

1. a fifth Computation Outcome or a combined Outcome;
2. a new Degraded State, partial-result state token, or third state axis;
3. a new, widened, redefined, inferred, or recaptured Provenance meaning;
4. “Measure Provenance” or another ungoverned Provenance specialization;
5. Calculation Temporal Claim or a renamed equivalent;
6. a new Canonical Temporal Claim grammar or Event Type;
7. a new or specialized Producing Domain;
8. a Result claiming Event Type `Snapshot Creation`;
9. a hidden, ambient, mutable, ranged, unversioned, or second dependency
   inventory;
10. a hidden semantic owner or ownership transfer through carriage,
    serialization, hashing, validation, custody, persistence, or display;
11. a new reason-code taxonomy, free-text semantic branch, runtime exception
    taxonomy, or provider reason taxonomy;
12. a fork or reinterpretation of `MSB1`, `OIM1`, Measurement Window bytes,
    WP3 numeric bytes, semantic versions, dependency versions, or failure
    classification;
13. a derived working value represented as witnessed M39 Observation evidence;
14. Observation identity inferred from provider, value, timestamp, payload, or
    semantic equality;
15. a value on non-success or a missing value on success;
16. a production formula, method, Definition/Method catalog entry, registry,
    resolver, kernel, or adoption;
17. Ledger, Portfolio, Workspace, Wealth, person, household, goal, preference,
    allocation, performance, execution, transaction, judgment,
    recommendation, trust, quality, evaluation, or presentation meaning;
18. runtime behavior, including retrieval, orchestration, retry, fallback,
    caching, replay, clock access, or error handling;
19. implementation behavior, data structures, libraries, modules, or
    algorithms beyond the normative mathematical and byte rules stated here;
20. persistence behavior, database schema, retention, indexing, or storage
    identity;
21. API, SDK, endpoint, transport, message, or UI behavior;
22. provider selection, provider behavior, adapter behavior, or preferred
    source; and
23. executable validation, tests, fixtures, runners, harnesses, or reference
    implementations.

---

## 17. Compatibility and Determinism Demonstration

### 17.1 Compatibility

- **M34:** existing Canonical Temporal Claim and Degraded State grammar is
  reused; no Asset identity is inferred; descriptive calculation remains
  separate from portfolio, judgment, execution, and presentation meaning.
- **M39:** exact Observation identity, source meaning, precision, and captured
  Provenance remain intact; derived values are not Observations.
- **M40:** the four-category input closure, four-value Outcome closure,
  Deterministic Calculation, no-value-on-non-success, and empty production
  catalog remain intact.
- **WP1:** no Definition, Method Version, Method Requirement, identity, or
  version rule changes.
- **WP2:** no Subject, Manifest, Manifest Entry, membership, count, order,
  identity, or byte changes.
- **WP3:** no Window, semantics, processing order, arithmetic, dependency, or
  classification rule changes.

### 17.2 Determinism proof obligations

| Required property | Normative closure | Golden Vector evidence |
|---|---|---|
| Deterministic Result identity | Closed §8 basis and SHA-256 rule | GV-B-01, GV-B-06–08 |
| Deterministic serialization | Closed member order and lexical rules | GV-B-01, GV-B-18 |
| Deterministic hash | One algorithm over one octet sequence | GV-B-01, GV-B-07–08 |
| Deterministic round trip | Injective decode/encode rule | GV-B-01, GV-B-09 |
| Deterministic lineage | Exact embedded identities and cardinality checks | GV-B-10, GV-B-13 |
| Deterministic Outcome closure | Exactly one frozen Outcome and value equivalence | GV-B-02–05 |
| Deterministic matrix behavior | Total 24-cell matrix and fixed shapes | GV-B-12 |
| Deterministic handoff | Exact-octet/version consumption | GV-B-14 |
| Deterministic partial composition | Six explicit preconditions and one disclosed shape | GV-B-15–16 |
| Deterministic reasons | Closed citation object and canonical tuple order | GV-B-17 |

No proof relies on a clock, locale, provider, library default, mutable
configuration, runtime, persistence, API, or executable artifact.

---

## 18. Acceptance Checklist

| Requirement | Result | Normative evidence |
|---|---|---|
| Normative Result schema | **SATISFIED** | §4 |
| Mandatory coordinates | **SATISFIED** | §§4.1, 4.6 |
| Optional coordinates | **SATISFIED** | §4.6 |
| Conditional coordinates | **SATISFIED** | §§4.6, 5, 6 |
| Cardinality | **SATISFIED** | §§4–5, 10 |
| Normative composition | **SATISFIED** | §§4, 12 |
| Success Result | **SATISFIED** | §6.2 |
| Non-success Result | **SATISFIED** | §6.3 |
| Exactly-one Outcome | **SATISFIED** | §6.1 |
| No value on non-success | **SATISFIED** | §6.4 |
| Outcome / Degraded State matrix | **SATISFIED** | §7 |
| Canonical Temporal Claim binding | **SATISFIED** | §4.4 |
| Calculation timestamp carriage | **SATISFIED** | §§4.4, 9.1 |
| Identity basis | **SATISFIED** | §8.1 |
| Canonical serialization | **SATISFIED** | §§3, 9 |
| Schema-version semantics | **SATISFIED** | §9.2 |
| Identity independence | **SATISFIED** | §§8.2, 8.4 |
| Hash stability | **SATISFIED** | §§8.3–8.4 |
| Round-trip determinism | **SATISFIED** | §9.3 |
| Lineage completeness | **SATISFIED** | §12.1 |
| WP3 handoff | **SATISFIED** | §§2.3, 12.3 |
| Partial-result composition | **SATISFIED** | §11 |
| Outcome reason representation | **SATISFIED** | §10 |
| Validation rules | **SATISFIED** | §13 |
| Positive/negative/identity/serialization/hash/round-trip/handoff/partial vectors | **SATISFIED** | §15 |
| Negative corpus | **SATISFIED** | §16 |
| No authority escalation | **SATISFIED** | §§1.3, 16 |

---

## 19. Final Normative Boundary

M41-WP4 Stage B begins with exact frozen WP1–WP3 coordinates and ends with one
immutable Market Measure Result whose Outcome, value presence, temporal claim,
Degraded State, Provenance carriage, lineage, identity basis, hash, full
serialization, round trip, handoff, and partial-composition behavior are
mechanically closed.

It changes no upstream authority and creates no downstream operational
authority. Two independent readers given the same semantic coordinates derive
the same identity-basis octets, Result identity, full Result octets, Outcome
closure, matrix cell, and lineage without an ambient default.

Implementation, runtime, provider, persistence, API, production-method, and
executable-validation authority remain `NONE`.

---

## Final Status

**READY FOR INDEPENDENT REVIEW**
