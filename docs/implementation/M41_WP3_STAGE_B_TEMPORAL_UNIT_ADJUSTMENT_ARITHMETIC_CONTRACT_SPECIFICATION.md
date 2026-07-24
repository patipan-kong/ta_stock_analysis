# M41-WP3 Stage B — Temporal, Unit, Adjustment, and Arithmetic Contract Specification

**Status:** COMPLETE — submitted for the separately authorized independent
review stage  
**Artifact type:** Normative governance specification  
**Implementation authority:** **NONE**  
**Production Definition or Method Version admission:** **NONE**  
**Registry, runtime, provider, persistence, API, and executable-validation
authority:** **NONE**

---

## 0. Executive determination

This specification closes every deterministic semantic choice allocated to
M41-WP3 by the approved WP3 Architecture and confirmed Stage A register. It
specifies:

- the concrete Measurement Window record, identity, canonical bytes, and
  validation;
- temporal selection, inclusive cutoff, qualified-time ordering, timezone,
  calendar, alignment, and DST semantics;
- missing-data, density, and interpolation semantics;
- unit, scale, basis, and currency compatibility;
- adjustment acceptance and exact calculation-side transformation;
- exact rational arithmetic, decimal quantization, canonical numeric bytes,
  and exceptional arithmetic;
- complete governed-dependency closure through the existing Method Version
  dependency-version list;
- one cross-dimension processing order and a total WP3 failure
  classification; and
- normative golden vectors `GV-01` through `GV-30`.

The specification introduces no governed vocabulary. It defines no formula
or production method, admits no Definition or Method Version, modifies no
WP1 or WP2 field, and creates no executable or operational authority.

Normative terms `MUST`, `MUST NOT`, `REQUIRED`, `MAY`, and `ONLY` apply to a
future conforming semantic specification or to the documentary vectors in
this artifact. They do not authorize implementation.

---

## 1. Authority, precedence, and scope

### 1.1 Authority order

This artifact is subordinate to, and MUST be read consistently with:

1. the frozen M34 constitutional decisions;
2. the frozen M39 Observation contracts;
3. the frozen M40 market-measure vocabulary and determinism contracts;
4. the confirmed M41 Architecture;
5. the frozen M41-WP1 contracts;
6. the frozen M41-WP2 contracts;
7. the approved M41-WP3 Architecture; and
8. the approved M41-WP3 Stage A Vocabulary Sufficiency and Semantic Surface
   Register.

On conflict, the earlier authority controls and this artifact has no power
to amend it.

### 1.2 Included

The normative surface is exactly Components A–I of the approved WP3
Architecture. The concrete Measurement Window is invocation-bound. All
selection, compatibility, transformation, arithmetic, dependency-use, and
failure-classification rules are method-governed semantics denoted by the
existing Method Version semantic version. Every output-affecting external
semantic facility is named only through that Method Version's existing
declared dependency-version list.

### 1.3 Excluded

This artifact does not:

- alter Market Measure Definition, Method Version, Method Requirement,
  Measure Subject, Observation Input Manifest, or Manifest Entry;
- retrieve, repair, merge, enrich, mutate, rank, or construct Observations
  or Manifests;
- define a Result, Measure Value, Provenance composition, reason code,
  partial-output envelope, Canonical Temporal Claim, or degraded-state
  interaction;
- authorize implicit FX, inferred unit, inferred currency, inferred
  adjustment, event adjudication, or source preference;
- define a production formula, method, registry entry, resolver, loader,
  kernel, service, endpoint, persistence model, provider behavior, cache,
  replay process, or UI; or
- commit an executable validator, reference implementation, or conformance
  harness.

WP4 remains the sole downstream owner of Result composition.

### 1.4 Placement invariant

No invocation-bound value may override method-governed semantics. No
method-governed rule may fill an omitted invocation value from a clock,
locale, host timezone, current dependency, network, provider convention,
configuration, cache, request time, or `latest`. Any change to a rule in
this specification requires a different Method Version semantic version.
Any change to an exact governed dependency identifier or version requires a
different existing Method Version identity under WP1.

---

## 2. Common canonical encoding

### 2.1 Octets and JSON subset

Measurement Window bytes and the documentary golden-vector bundles use the
following closed canonical JSON subset:

1. encoding is UTF-8 without a byte-order mark;
2. no whitespace occurs outside strings;
3. object member order is the order specified by this artifact;
4. duplicate member names are prohibited;
5. strings use JSON quotation; quotation mark, reverse solidus, and control
   characters use the shortest JSON escape; all other characters are
   encoded directly as UTF-8;
6. only objects, arrays, strings, `true`, `false`, and `null` occur;
7. JSON number tokens do not occur; governed integers, decimals, and
   rationals are strings under §2.2;
8. arrays preserve semantic order and MUST NOT be treated as sets unless an
   upstream frozen contract already defines their canonical set order; and
9. an unknown, additional, omitted, reordered, or non-canonically escaped
   member is non-canonical.

Canonical decoding is injective: exactly one logical value maps to exactly
one octet sequence. Decode followed by encode MUST reproduce the input
octets exactly. These rules do not alter WP2 serialization.

### 2.2 Canonical numeric forms

WP3 arithmetic has three exact domains:

| Domain | Canonical lexical form | Constraints |
|---|---|---|
| integer | `I:<n>` | `<n>` is `0` or `-?[1-9][0-9]*`; `-0`, leading zeroes, plus signs, and whitespace are prohibited |
| decimal | `D:<c>E<e>` | value is integer coefficient `<c>` times 10 to integer exponent `<e>`; zero is only `D:0E0`; nonzero `<c>` has no trailing zero; `<c>` and `<e>` use the integer grammar without `I:` |
| rational | `R:<p>/<q>` | `<q>` is positive; `gcd(abs(p),q)=1`; zero is only `R:0/1`; `<p>` and `<q>` use the integer grammar without `I:` |

Examples are `I:-12`, `D:125E-2` for 1.25, and `R:-1/8`. `D:1250E-3`,
`D:-0E4`, `R:2/4`, and `R:0/9` are non-canonical.

Every integer and decimal denotes an exact rational. Arithmetic is performed
over unbounded mathematical integers and reduced rationals until an exact
quantization point declared by the Method Version semantics. “Unbounded” is
a normative mathematical property, not an implementation requirement.

### 2.3 Decimal quantization

A quantization instruction consists of an integer output scale `s`, meaning
an increment of `10^-s`, and exactly one of:

- `toward_zero`;
- `toward_positive`;
- `toward_negative`;
- `half_even`;
- `half_up`; or
- `half_down`.

For exact value `x`, let `y=x*10^s`. Adjacent integers bound `y`.
Directed modes select the integer in their named direction. A half mode
selects the nearest integer; at an exact half:

- `half_even` selects the even adjacent integer;
- `half_up` selects the adjacent integer with greater absolute value; and
- `half_down` selects the adjacent integer with smaller absolute value.

The selected integer `n` denotes `n*10^-s` and is then encoded in the unique
canonical decimal form. Output scale is semantic metadata supplied to WP4;
it is not represented by trailing zeroes in the canonical number. No
rounding occurs merely because a decimal is encoded.

### 2.4 Canonical semantic-choice encodings

All ordinary semantic-choice tokens defined in this artifact are lowercase
ASCII with underscore separators. They are case-sensitive and are encoded
as JSON strings. Identifiers and versions imported from frozen authorities
retain their authority-defined bytes. Where that authority permits more
than one textual representation, a Method Version MUST identify the one
canonical representation it uses; otherwise the dependency is unresolved.

---

## 3. Measurement Window contract

### 3.1 Closed record

A Measurement Window has exactly these members in exactly this order:

```json
{"schema_version":"m41-wp3.measurement-window/1","window_kind":"elapsed","manifest_identity":"hex:4f494d31","start":{"precision":"instant","value":"2025-01-01T00:00:00Z","disambiguation":"not_applicable"},"start_edge":"inclusive","cutoff":{"precision":"instant","value":"2025-01-02T00:00:00Z","disambiguation":"not_applicable"},"cutoff_edge":"inclusive","time_basis":"elapsed","timezone_ref":{"kind":"utc","identifier":"UTC","version":"fixed"},"calendar_ref":{"kind":"none","identifier":"none","version":"none"},"count":"I:0"}
```

The example illustrates field order only. For an `elapsed` window,
`count:"I:0"` is the correct value. The example record is nevertheless
non-conforming solely because its truncated `manifest_identity` value
`hex:4f494d31` is not a complete WP2 §5.8 Manifest canonical byte sequence.
The fields are:

| Field | Cardinality | Contract |
|---|---:|---|
| `schema_version` | 1 | exact token `m41-wp3.measurement-window/1` |
| `window_kind` | 1 | `elapsed`, `civil`, `session`, or `observation_count` |
| `manifest_identity` | 1 | exact canonical bytes of the already-valid WP2 Manifest encoded as `hex:` followed by two lowercase hexadecimal digits per byte, with no separator |
| `start` | 1 | boundary object or `null`, as constrained below |
| `start_edge` | 1 | `inclusive`, `exclusive`, or `not_applicable` |
| `cutoff` | 1 | boundary object; never `null` |
| `cutoff_edge` | 1 | exact token `inclusive` |
| `time_basis` | 1 | `elapsed`, `civil`, `session`, or `observation_count`, equal to `window_kind` |
| `timezone_ref` | 1 | exact timezone-reference object |
| `calendar_ref` | 1 | exact calendar-reference object |
| `count` | 1 | positive canonical integer for `observation_count`; otherwise exact token `I:0` |

A boundary object has members in order `precision`, `value`,
`disambiguation`. `precision` is `instant`, `local_datetime`, or `date`.

- An `instant` value is `YYYY-MM-DDThh:mm:ssZ`, is a UTC instant, and has
  `disambiguation:"not_applicable"`.
- A `local_datetime` value is `YYYY-MM-DDThh:mm:ss`, carries no offset, and
  has `disambiguation` equal to `reject`, `earlier_offset`, or
  `later_offset`.
- A `date` value is `YYYY-MM-DD` and has
  `disambiguation:"not_applicable"`.

Years use four digits `0001`–`9999`; month, day, hour, minute, and second use
two digits and MUST form a valid proleptic-Gregorian civil value. Leap
seconds are not representable. Fractional seconds and numeric-offset
boundary strings are prohibited; fixed offsets belong in `timezone_ref`.

A timezone-reference object has members in order `kind`, `identifier`,
`version`:

- `utc`: identifier `UTC`, version `fixed`;
- `fixed_offset`: identifier is `+hh:mm` or `-hh:mm`, with absolute offset
  no greater than 23:59, and version `fixed`;
- `named_zone`: exact dependency identifier and exact dependency version;
  or
- `not_applicable`: identifier and version are both `none`.

A calendar-reference object has members in the same order:

- `none`: identifier and version are both `none`; or
- `named`: exact governed calendar dependency identifier and version.

### 3.2 Permitted forms

The Method Version semantics MUST select exactly one permitted form:

| Kind | `start` / `cutoff` | Timezone | Calendar | Edge |
|---|---|---|---|---|
| `elapsed` | both `instant`; start strictly earlier than cutoff | `utc`, `fixed_offset`, or `not_applicable`; it cannot alter instant meaning | `none` | start `inclusive` or `exclusive`; cutoff `inclusive` |
| `civil` | both `local_datetime` or both `date`; resolved start strictly earlier than cutoff | `utc`, `fixed_offset`, or `named_zone`; not `not_applicable` | `none` or exact `named` if civil-day validity depends on it | start `inclusive` or `exclusive`; cutoff `inclusive` |
| `session` | both `date`; each date denotes the governed session boundary selected by Method Version semantics | explicit timezone through the exact calendar dependency or exact named/fixed reference required by it | exact `named` | start `inclusive` or `exclusive`; cutoff `inclusive` |
| `observation_count` | start is `null`; cutoff is `instant`; `count` is positive | `utc` or `not_applicable` | `none` | start `not_applicable`; cutoff `inclusive` |

An absent start is permitted only for `observation_count`, whose positive
count is the explicit lower bound after cutoff filtering and semantic
ordering. No other absence or `null` is valid.

### 3.3 Identity, immutability, and rejection

Measurement Window identity is its complete canonical octet sequence. A
digest may be a future custody convenience but is not canonical identity
and is not specified here. All fields participate in identity, including
the lossless byte-for-byte Manifest identity representation and exact
dependency versions. Decoding the `manifest_identity` hexadecimal MUST
reproduce the complete WP2 §5.8 Manifest canonical bytes; a digest,
surrogate identifier, or presentation label is invalid. The record is
immutable; changing any logical value creates a distinct window.

A window is non-conforming and maps to `INSUFFICIENT_INPUT` for the
invocation when:

- any required field is absent, additional, contradictory, unresolved,
  ambiguous, invalid, or non-canonical;
- a dependency reference is absent from, or disagrees with, the Method
  Version dependency-version list;
- its kind is not the kind required by the exact Method Version semantics;
- its Manifest identity is not the supplied Manifest identity;
- its resolved start is not strictly earlier than its cutoff;
- `count` violates §3.1 or §3.2; or
- local time cannot be resolved under §5.

This classification does not create a Result or reason field.

---

## 4. Temporal selection, cutoff, and semantic ordering

### 4.1 Role declaration

For every input role, exact Method Version semantics MUST declare one
source-established M39 temporal meaning used for selection and ordering:
observation time, occurrence time, effective time, publication time, or
reference period. A role MUST also declare whether the chosen meaning is an
instant, date, interval, or M39-qualified approximate value. One role may
not silently substitute another temporal meaning.

If the required meaning or qualification is absent, contradictory, or
cannot be compared without strengthening its M39 precision, the input
prerequisite is not satisfied and the outcome is `INSUFFICIENT_INPUT`.

### 4.2 Lower boundary and inclusive cutoff

For an instant or date point `t`:

- an inclusive lower edge admits `t` when `start <= t`;
- an exclusive lower edge admits `t` when `start < t`; and
- the cutoff admits `t` when `t <= cutoff`.

The cutoff is always inclusive. Evidence strictly later than cutoff MUST
NOT participate, even if it was already present in the Manifest. Retrieval,
ingestion, or storage time cannot replace the declared semantic time.

For an interval `[a,b]` with source-established endpoint inclusion retained
from M39, the Method Version MUST declare one of two rules:

- `contained`: admit only when every included point of the source interval
  lies inside the Measurement Window; or
- `overlap`: admit when the intersection contains at least one point after
  applying both sets of endpoint rules.

No clipping is implied. If clipping is mathematically required, the exact
Method Version semantics must declare it as derived working material; it
does not mutate the Observation.

For `observation_count`, apply the inclusive cutoff, order under §4.4, and
select the last `count` entries. Fewer entries is `INSUFFICIENT_INPUT`.

### 4.3 Qualified and approximate time

A date-only value remains a date. It may be compared only to date
boundaries under an explicit civil or session rule. It MUST NOT be assigned
midnight, noon, session close, or an instant by convention.

An approximate instant or interval is admitted only if the Method Version
declares `contained` or `overlap` for that qualification. It retains its
uncertainty. When exact ordering of overlapping qualified times cannot be
established, §4.4's Observation Identity tie-break orders them only after
their complete source-established temporal coordinate; it does not assert
which event occurred first.

### 4.4 Multi-role alignment and stable ordering

Each role MUST declare a common alignment coordinate: exact instant, civil
date, governed session label, or explicit ordinal expected position.
Coordinates of different kinds are incompatible unless an exact rule and
all required dependencies convert them without fabricating source
precision.

Semantic input ordering is ascending lexicographic order of:

1. role code-point bytes;
2. the complete normalized source-established temporal coordinate,
   including its meaning, precision, lower and upper values, endpoint
   inclusion, uncertainty, timezone qualification, and calendar
   qualification;
3. the exact frozen M39 Observation Identity bytes.

This is a calculation view only. It does not reorder, reserialize, or alter
the WP2 Manifest. Provider order, Manifest presentation order, retrieval
order, row order, map order, and operational timestamps have no semantic
effect.

Two identity-distinct Observations at one role and expected position are a
duplicate under §6.2. The tie-break makes processing deterministic but does
not authorize choosing one as preferred evidence.

---

## 5. Timezone, calendar, alignment, and DST

### 5.1 Time bases

- `elapsed` uses exact UTC-second distance between instants.
- `civil` advances proleptic-Gregorian fields in the declared timezone and
  then resolves the resulting local boundary.
- `session` advances only session labels supplied by the exact named
  calendar dependency.
- `observation_count` counts selected identity-distinct Observations and
  performs no duration inference.

These bases are not interchangeable. A Method Version MUST declare exact
duration amount, civil unit, session count, or Observation count wherever
it derives a start or expected positions.

### 5.2 Named-zone and fixed-offset resolution

A fixed offset is applied exactly and has no DST. A named-zone reference is
valid only when its identifier and version exactly match a declared
governed dependency. The dependency supplies the complete offset-transition
mapping. Host timezone and an unversioned “current” timezone database are
irrelevant.

For a nonexistent local time in a DST gap, only
`disambiguation:"reject"` is conforming; `earlier_offset` and
`later_offset` are invalid because no occurrence exists. The invocation is
`INSUFFICIENT_INPUT`.

For an ambiguous local time in a fold:

- `earlier_offset` selects the occurrence with the UTC instant that occurs
  first;
- `later_offset` selects the occurrence with the UTC instant that occurs
  second; and
- `reject` rejects the boundary as `INSUFFICIENT_INPUT`.

For an unambiguous local time, all three tokens resolve to its sole
occurrence, but the exact token remains identity-significant.

### 5.3 Calendar semantics

A session or holiday-sensitive civil rule MUST name an exact calendar
dependency and version. That dependency alone determines valid sessions,
holidays, early closes, irregular sessions, and session boundary instants.
Weekday arithmetic, exchange name, a 252-session assumption, machine
locale, and provider convention are prohibited substitutes.

The Method Version MUST state:

- whether start/cutoff date denotes session open, session close, or a
  dependency-defined boundary;
- whether a non-session boundary date is rejected, truncated inward to the
  next/previous session, or extended outward to the next/previous session;
- the exact alignment origin; and
- whether partial periods are retained or rejected.

There is no default truncation, extension, or partial-period rule.

### 5.4 Leap days and alignment

Civil month/year advancement uses the same day number when it exists. If it
does not exist, exact Method Version semantics MUST choose `reject` or
`last_day`; there is no default. Period alignment uses an explicit origin
and half-open construction boundaries before the Measurement Window edge
rules are applied. Session alignment uses only the exact calendar's ordered
session labels.

---

## 6. Missing data and density

### 6.1 Required per-role closure

Every role MUST declare exactly one treatment:

- `reject`;
- `omit`;
- `exact_density`;
- `interpolate`; or
- `independently_complete_coordinates`.

It MUST also declare the expected-position generator, density basis,
boundary-gap rule, interior-gap rule, maximum gap in explicit units or
`none`, duplicate treatment, and denominator effect. An incomplete
declaration is not a usable Method Version semantic specification and
cannot be admitted under WP1.

`independently_complete_coordinates` is permitted only when the frozen
Market Measure Definition declares separable output coordinates and WP4
permits their Result composition. This artifact does not grant either
permission.

### 6.2 Expected positions, gaps, duplicates, and density

Expected positions are generated solely by one declared basis:

- elapsed instants from an exact origin and exact duration;
- civil positions from an exact origin, unit, timezone, and leap rule;
- governed sessions from an exact calendar and version; or
- explicit ordinal positions.

A gap is an expected position with no conforming Observation. A boundary
gap is the first or last expected position missing; all others are interior
gaps. A duplicate is more than one identity-distinct Observation for one
role and expected position. Identical Manifest references are not counted
twice merely because two requirement keys cite the same Observation under
the frozen WP2 rule.

Density is `present_positions / expected_positions` as an exact reduced
rational, after temporal selection and duplicate detection but before
omission or interpolation. It is never row count per wall-clock duration
unless that exact elapsed basis is declared.

Duplicates are `INSUFFICIENT_INPUT` unless exact Method Version semantics
mathematically combine all duplicate values in stable §4.4 order. Source
preference and silent first/last choice are prohibited.

### 6.3 Treatment rules

- `reject`: any prohibited boundary gap, interior gap, duplicate, or density
  failure yields `INSUFFICIENT_INPUT`.
- `exact_density`: success requires exact equality to the declared reduced
  rational threshold and all additional gap constraints.
- `omit`: only positions satisfying the exact omission predicate are
  removed. The Method Version MUST say whether each downstream denominator
  uses retained count, original expected count, elapsed span, or another
  exact declared coordinate.
- `interpolate`: only interior gaps no larger than the exact maximum may be
  constructed. Both bounding endpoints are required and must already share
  accepted basis, compatible normalized unit, currency, and scale.
- `independently_complete_coordinates`: an incomplete coordinate is not
  calculated; no value placeholder is made here.

Boundary interpolation is prohibited. Forward fill, backward fill, zero
fill, nearest-value choice, weekend fill, and silent omission are prohibited
unless they are the exact declared mathematical `omit` or `interpolate`
rule; labels alone are insufficient.

### 6.4 Linear interpolation

When `interpolate` selects linear interpolation, for expected coordinate
`t` strictly between endpoints `(t0,x0)` and `(t1,x1)`, the working value is:

`x0 + (x1 - x0) * (t - t0) / (t1 - t0)`.

All coordinate differences and values are exact rationals. No rounding
occurs unless the Method Version declares one exact post-interpolation
quantization point. The derived value is working material only: it is not
an Observation, does not receive Observation Identity or provenance, and
MUST NOT be inserted into or alter the Manifest.

---

## 7. Unit and currency compatibility

### 7.1 Required qualification

Every numeric input role and arithmetic output coordinate MUST declare:

- numeric domain: integer, decimal, or rational;
- canonical unit expression;
- multiplicative scale relative to that expression;
- basis/adjustment qualification; and
- currency code or exact token `not_applicable`.

An input whose M39 evidence lacks a meaningful required qualification is
`INSUFFICIENT_INPUT`. Asset Registry, Asset Definition, another
Observation, provider convention, or invocation default may not fill it.

### 7.2 Unit expressions

A canonical unit expression is a product of base-unit identifiers raised to
nonzero canonical integer exponents. Factors are ordered by ascending
Unicode code point of the authority-owned identifier. Exponent `1` is
written explicitly. The empty product is `1` and is dimensionless.

Two units are equal only when their canonical factor/exponent sequences,
scale, basis, and meaningful currency are equal. They are compatible when
their factor/exponent sequences and basis are equal and an exact declared
normalization can make scale equal. A normalization that uses a table,
taxonomy, factor, or algorithm is permitted only through an exact governed
dependency in the Method Version list.

A ratio of equal compatible dimensions is dimensionless after exact
normalization. A percentage is a dimensionless ratio with scale `R:1/100`.
A rate retains its denominator unit and exponent. Compound-unit
multiplication adds exponents; division subtracts them; zero exponents are
removed; factors are re-sorted.

### 7.3 Currency

Currency is compatible only when:

- both operands carry the same explicit authority-defined currency code;
- currency is `not_applicable` for both; or
- the exact Method Version formula is provably currency-invariant because
  equal-currency dimensions cancel separately before any cross-currency
  combination.

WP3 authorizes no currency conversion. Different currencies cannot be
normalized by this contract. Already-normalized evidence may be consumed
only if it is independently authorized under the frozen four-category input
closure and retains its explicit source qualification.

Missing or incompatible unit, basis, scale, or currency is
`INSUFFICIENT_INPUT`. Failure to resolve an exactly declared normalization
dependency is `DEPENDENCY_UNRESOLVED`.

---

## 8. Adjustment and basis

### 8.1 Basis distinction

The following ordinary qualifications remain distinct:

- `raw`: source-reported without the adjustment required by the calculation;
- `source_adjusted`: source-reported with the exact source-established
  adjustment qualification; and
- `calculation_normalized`: derived working material transformed by an
  exact Method Version rule.

These tokens do not reclassify M39 evidence or Structural Events. Every role
MUST declare accepted input basis. A basis mismatch is
`INSUFFICIENT_INPUT` unless an exact transformation is allowed.

### 8.2 Allowed transformation

An allowed transformation MUST declare:

1. the accepted source basis and target working basis;
2. exact Structural Event or other already-authorized evidence references;
3. every output-affecting dependency identifier and exact version;
4. an exact rational adjustment factor for each affected coordinate;
5. whether the factor multiplies or divides;
6. the applicability boundary and endpoint rule; and
7. any exact post-adjustment quantization.

Absent, ambiguous, or conflicting evidence is `INSUFFICIENT_INPUT`.
Failure to resolve an exact declared adjustment dependency is
`DEPENDENCY_UNRESOLVED`. Division by a zero factor after valid and sufficient
inputs is `FAILED`.

No discontinuity, ticker change, provider label, Registry field, or
Structural Event may be used to infer a factor or event. The transformation
does not mutate an Observation, create a Structural Event, change a
Definition Version, or compose WP4 Provenance.

### 8.3 Adjustment arithmetic

Factors use §2.2 exact numeric forms and are converted to reduced rationals.
Multiplication or division is exact. Rounding occurs only at the declared
post-adjustment quantization point. Provider-adjusted evidence and
calculation-normalized working material remain semantically distinct even
when their numeric values happen to be equal.

---

## 9. Arithmetic semantics

### 9.1 Normative model

All admitted canonical numeric inputs are converted exactly to reduced
rationals. Addition, subtraction, multiplication, division, integer powers,
comparison, and the linear interpolation of §6.4 use exact rational
arithmetic. Operation order is the exact syntax-tree order declared by the
Method Version; associativity, distributivity, constant folding, or
algebraic rearrangement MUST NOT move a quantization point or otherwise
change canonical output.

There is no intermediate precision limit. Intermediate rounding is
prohibited unless an exact operation boundary, scale, and rounding mode are
declared. Output is quantized once at the declared output boundary unless
other exact quantization points are part of the Method Version semantics.

### 9.2 Exceptional values and errors

NaN, positive infinity, and negative infinity are outside all accepted
domains and cannot be successful values. A non-canonical or exceptional
supplied input is `INSUFFICIENT_INPUT`.

After all inputs and dependencies are valid and sufficient:

- division by zero;
- even root of a negative value;
- logarithm of a nonpositive value;
- an operation outside its exact declared domain; or
- inability to produce every required arithmetic coordinate

is `FAILED`.

Mathematical overflow and underflow do not exist in the normative unbounded
model. A future bounded implementation that cannot represent a required
exact value is non-conforming; it may not substitute infinity, zero, a
clamped value, or a platform exception as semantic output.

### 9.3 Negative zero and output bytes

Negative zero is not a logical value. Any exact operation producing zero
encodes it as `I:0`, `D:0E0`, or `R:0/1` according to the declared output
domain. Supplied `-0` is non-canonical and therefore
`INSUFFICIENT_INPUT`.

The WP3 arithmetic handoff is the UTF-8 octet sequence of the canonical
numeric lexical form in §2.2, without quotation marks or terminator,
together with separately declared type, unit, scale, basis, currency,
output-scale, and semantic/dependency-version coordinates. WP4 owns how
those coordinates are composed into Measure Value and Result bytes.

Binary floating point, library decimal contexts, processor modes, locale,
and platform formatting have no normative status.

---

## 10. Governed dependency closure

### 10.1 Sole inventory

The existing Method Version declared dependency-version list is the sole
dependency inventory. WP3 creates no Dependency Manifest. A dependency is
required whenever output may depend on a named-zone rules source, calendar,
unit-normalization table/taxonomy/factor/algorithm, adjustment facility,
interpolation facility, or arithmetic facility whose version affects
meaning.

A fully specified rule intrinsic to the Method Version semantics needs no
separate dependency merely because a future implementation uses a library.

### 10.2 Exact closure

Before semantic use, every required dependency MUST:

1. occur exactly once in the Method Version list;
2. have an exact identifier and exact version, never a range or `latest`;
3. be ordered under WP1's frozen ascending code-point rule;
4. resolve to exactly one semantic authority with matching identity and
   version; and
5. supply the exact canonical material required by the Method Version
   semantics.

Absent, duplicate, ambiguous, mismatched, unavailable, or semantically
incomplete resolution is `DEPENDENCY_UNRESOLVED`. Invocation parameters
cannot replace or override a declared version.

Environment discovery, package-manager state, network lookup, mutable global
configuration, host-installed data, and current-date selection are
prohibited semantic inputs. Runtime custody never transfers semantic
ownership. Changing a dependency identifier or version changes Method
Version identity under frozen WP1 even when observed output happens not to
change.

---

## 11. Cross-dimension processing order

The following order is mandatory and non-commutative:

1. confirm the exact Market Measure Definition, Method Version semantic
   version, declared dependency-version list, Subject, Manifest, and
   invocation-bound parameter closure under frozen WP1/WP2;
2. resolve every required governed dependency exactly under §10; if any
   resolution fails, stop with `DEPENDENCY_UNRESOLVED`;
3. decode and validate canonical Measurement Window bytes and bind the exact
   Manifest identity;
4. inspect source-established M39 temporal and qualification coordinates
   without mutation;
5. apply temporal role selection, lower edge, inclusive cutoff, alignment,
   and stable semantic ordering;
6. validate required type, unit, scale, currency, and accepted basis;
7. apply exact adjustment transformations to create basis-qualified working
   values;
8. apply exact unit/scale normalization to compatible working values;
9. generate expected positions, detect duplicates and gaps, enforce density,
   and apply the declared omit/interpolation treatment;
10. evaluate the exact Method Version arithmetic syntax tree, including only
    declared intermediate quantization points;
11. apply final output quantization and canonical numeric encoding; and
12. hand WP4 either canonical arithmetic coordinates or one frozen
    Computation Outcome classification.

No later stage may repair an earlier rejection. In particular, interpolation
cannot supply a missing currency or basis; unit normalization cannot perform
FX; adjustment cannot infer an event; arithmetic cannot admit post-cutoff
evidence.

---

## 12. Failure classification

### 12.1 Total mapping

| WP3 condition | Frozen Computation Outcome |
|---|---|
| canonical supplied inputs fail a declared prerequisite, including invalid window; absent/ambiguous temporal meaning; insufficient count; gap/density/duplicate rejection; missing/incompatible type, unit, scale, basis, or currency; non-canonical/exceptional supplied number; missing/ambiguous/conflicting adjustment evidence | `INSUFFICIENT_INPUT` |
| exact declared governed dependency is absent, ambiguous, mismatched, unavailable, version-incomplete, or otherwise cannot resolve exactly | `DEPENDENCY_UNRESOLVED` |
| semantically valid and sufficiently supplied arithmetic reaches division by zero, invalid operation, exact domain error, or cannot complete all required coordinates | `FAILED` |
| all required coordinates complete and canonical arithmetic bytes exist | `SUCCEEDED` |

If multiple conditions are observable, the §11 order controls. Dependency
closure precedes input conformance; therefore a required unresolved
dependency classifies `DEPENDENCY_UNRESOLVED` without speculating about
later input or arithmetic conditions. After dependencies resolve,
prerequisite insufficiency precedes arithmetic. `FAILED` is possible only
after semantic validity and sufficiency have been established.

This table reuses frozen meanings. It does not define Result contents,
reason representation, partial values, or degraded-state interaction.

---

## 13. Field-level five-part ownership-boundary gate

| Field or rule group | Permitted subject | Permitted inputs | Descriptive output meaning | Ledger/Portfolio/Workspace/Wealth excluded | Judgment/evaluation excluded | Result |
|---|---|---|---|---|---|---|
| Measurement Window fields, bytes, identity | exact input-selection boundary over one frozen Manifest | explicit boundaries, timezone/calendar reference, Manifest identity | immutable deterministic selection boundary | Yes | Yes | Pass |
| temporal role, edge, cutoff, interval, alignment, order | already-bound Measure Subject and exact M39 evidence | source-established time and exact Method Version rules | selected and semantically ordered evidence | Yes | provider/source preference excluded | Pass |
| timezone/calendar/DST fields and rules | same | explicit references and exact governed dependencies | deterministic civil/session resolution | Yes | convention/suitability excluded | Pass |
| missing-data/density/interpolation fields and rules | same | exact evidence, expected-position rule, explicit parameters | deterministic conformance or working values | Yes | quality ranking/best effort excluded | Pass |
| type/unit/scale/basis/currency fields and rules | same | exact M39 qualifications, Unit Semantics, authorized Asset references | compatibility or exact normalization | Yes | preferred unit/currency excluded | Pass |
| adjustment fields and rules | same | source basis, exact authorized evidence and dependencies | attributable calculation-side working basis | Yes | event inference/source preference excluded | Pass |
| numeric domain/scale/rounding/operation fields and rules | same | canonical numbers and explicit parameters | exact canonical arithmetic bytes | Yes | confidence/correctness verdict excluded | Pass |
| dependency identifier/version use | same | existing Method Version dependency list | deterministic semantic closure | Yes | package/source trust excluded | Pass |
| order and outcome classification | same | conforming outputs of preceding stages | canonical bytes or frozen outcome meaning | Yes | no new verdict axis | Pass |

No row creates ownership outside Market Intelligence's WP3 allocation; no
row transfers upstream ownership or enters WP4 composition.

---

## 14. Compatibility and non-leakage

### 14.1 M34

The contract does not infer Asset identity/classification from evidence,
does not substitute Measurement Window for Canonical Temporal Claim, and
contains no Portfolio, Wealth, judgment, evaluation, recommendation,
execution, or presentation meaning.

### 14.2 M39

Observation identity, temporal precision, unit, currency, scale, basis,
absence, uncertainty, and provenance remain source-faithful. Selection and
working transforms do not mutate, merge, strengthen, or invent an
Observation. Numeric equality never collapses identity-distinct evidence.

### 14.3 M40

The four-category input closure, explicit cutoff/window, absence of ambient
defaults, explicit units, prohibition of implicit FX and inferred
adjustment, deterministic arithmetic, exact dependency versioning, and
four-value Computation Outcome closure are preserved.

### 14.4 WP1

No field, identity coordinate, Method Requirement operand/grammar, or
admission disposition changes. Method-governed rules are semantics denoted
by the existing semantic version; dependencies use the existing list.

### 14.5 WP2

The supplied Measure Subject and Manifest are already valid and immutable.
Measurement Window adds no WP2 field. Semantic input order is a calculation
view and never changes Manifest membership, count, order, identity, or
bytes.

### 14.6 WP4 handoff

WP3 hands off the exact Measurement Window bytes/identity, exact semantic
and dependency versions, exact qualified canonical arithmetic bytes on
success, or one frozen outcome classification. WP3 does not define the
Result envelope or any WP4-owned coordinate.

---

## 15. Golden-vector conventions

The 30 vectors below are normative documentation/data fixtures. Their
single-line `input bytes` and `expected bytes` code spans contain the exact
UTF-8 bytes between the backticks, with no newline. They use the canonical
JSON subset in §2 only as a compact documentary bundle; the bundle member
names are not a production record, API, registry, or new governed
vocabulary.

In every input bundle:

- `sv` is the exact fixture-only Method Version semantic-version label;
- `deps` is the exact ordered fixture-only dependency identifier/version
  list;
- `w` contains exact canonical Measurement Window bytes as a JSON string
  when the window itself is under test, or `none` otherwise;
- `in` contains the complete material facts needed for the proof; and
- `rule` is the exact fixture rule choice.

The fixture-only dependency facts are:

| Identifier/version | Exact documentary meaning |
|---|---|
| `fixture.tz/1` | local `2025-03-30T02:30:00` is nonexistent; on `2025-10-26`, local 02:30 maps earlier to `00:30:00Z` and later to `01:30:00Z` |
| `fixture.calendar/1` | 2025-07-04 is closed; 2025-07-03 closes at 17:00Z; 2025-07-07 closes at 20:00Z |
| `fixture.unit/1` | `cm` normalizes to `m` by factor `R:1/100` |
| `fixture.unit/2` | `cm` normalizes to `m` by factor `R:1/10` solely to prove version sensitivity |
| `fixture.adjust/1` | cited event `E1` supplies multiplicative factor `R:1/2` before 2025-01-03 |

These rows are inline evidence, not dependency registry entries. Every
vector explicitly admits no production Definition, Method Version, formula,
or method. Window fixtures use complete frozen WP2 canonical Manifest bytes:
the `M1` fixture is one `single_asset` subject (`A`, role `r`) and one entry
(`q`, Observation Identity reference `O1`), encoded as
`4f494d310000000f4d5342310100000001410000000172000000010000000171000000024f31`;
the `M30` fixture differs only by the three-byte Observation Identity
reference `O30` and ends
`0000000171000000034f3330`. These fixture facts assert that `q`, `O1`, and
`O30` are valid under the bound frozen authorities; they do not admit them
as production records.

---

## 16. Normative golden vectors

### GV-01 — Window start edge

- Rule: elapsed point selection; inclusive versus exclusive lower edge,
  inclusive cutoff.
- Semantic/dependency versions: `gv-01/1`; none.
- Input bytes: `{"sv":"gv-01/1","deps":[],"w":"{\"schema_version\":\"m41-wp3.measurement-window/1\",\"window_kind\":\"elapsed\",\"manifest_identity\":\"hex:4f494d310000000f4d5342310100000001410000000172000000010000000171000000024f31\",\"start\":{\"precision\":\"instant\",\"value\":\"2025-01-01T00:00:00Z\",\"disambiguation\":\"not_applicable\"},\"start_edge\":\"inclusive\",\"cutoff\":{\"precision\":\"instant\",\"value\":\"2025-01-02T00:00:00Z\",\"disambiguation\":\"not_applicable\"},\"cutoff_edge\":\"inclusive\",\"time_basis\":\"elapsed\",\"timezone_ref\":{\"kind\":\"utc\",\"identifier\":\"UTC\",\"version\":\"fixed\"},\"calendar_ref\":{\"kind\":\"none\",\"identifier\":\"none\",\"version\":\"none\"},\"count\":\"I:0\"}","in":[["O1","2025-01-01T00:00:00Z"],["O2","2025-01-02T00:00:00Z"]],"rule":"point"}`
- Expected bytes: `["O1","O2"]`
- Derivation: both points satisfy `start <= t <= cutoff`. Replacing only
  `start_edge` with `exclusive` produces `["O2"]`; the changed byte changes
  window identity.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-02 — Inclusive cutoff

- Rule: cutoff is inclusive and post-cutoff evidence is excluded.
- Semantic/dependency versions: `gv-02/1`; none.
- Input bytes: `{"sv":"gv-02/1","deps":[],"w":"none","in":[["O1","2025-01-02T00:00:00Z"],["O2","2025-01-02T00:00:01Z"]],"rule":"cutoff=2025-01-02T00:00:00Z"}`
- Expected bytes: `["O1"]`
- Derivation: `O1` equals the cutoff; `O2` is one second later.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-03 — Elapsed duration versus civil calendar

- Rule: subtract one elapsed day versus one civil day across a 23-hour
  civil day.
- Semantic/dependency versions: `gv-03/1`; `fixture.tz/1`.
- Input bytes: `{"sv":"gv-03/1","deps":[["fixture.tz","1"]],"w":"none","in":{"cutoff":"2025-03-30T03:30:00+02:00","elapsed":"P1D","civil":"P1D"},"rule":"compare_start"}`
- Expected bytes: `{"civil_start":"2025-03-29T03:30:00+01:00","civil_span_seconds":"I:82800","elapsed_start":"2025-03-29T02:30:00+01:00","elapsed_span_seconds":"I:86400"}`
- Derivation: the declared transition removes one civil hour; exact elapsed
  subtraction remains 86,400 seconds.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-04 — Host-timezone independence

- Rule: canonical window is UTC and never consults host timezone.
- Semantic/dependency versions: `gv-04/1`; none.
- Input bytes: `{"sv":"gv-04/1","deps":[],"w":"{\"schema_version\":\"m41-wp3.measurement-window/1\",\"window_kind\":\"elapsed\",\"manifest_identity\":\"hex:4f494d310000000f4d5342310100000001410000000172000000010000000171000000024f31\",\"start\":{\"precision\":\"instant\",\"value\":\"2025-01-01T00:00:00Z\",\"disambiguation\":\"not_applicable\"},\"start_edge\":\"inclusive\",\"cutoff\":{\"precision\":\"instant\",\"value\":\"2025-01-01T01:00:00Z\",\"disambiguation\":\"not_applicable\"},\"cutoff_edge\":\"inclusive\",\"time_basis\":\"elapsed\",\"timezone_ref\":{\"kind\":\"utc\",\"identifier\":\"UTC\",\"version\":\"fixed\"},\"calendar_ref\":{\"kind\":\"none\",\"identifier\":\"none\",\"version\":\"none\"},\"count\":\"I:0\"}","in":["host=UTC-08:00","host=UTC+07:00"],"rule":"ignore_host"}`
- Expected bytes: `{"end":"2025-01-01T01:00:00Z","identity_equal":true,"start":"2025-01-01T00:00:00Z"}`
- Derivation: host labels are not Measurement Window fields or semantic
  inputs; both reconstructions reproduce the literal `w` octets.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-05 — DST gap

- Rule: nonexistent local boundary with `reject`.
- Semantic/dependency versions: `gv-05/1`; `fixture.tz/1`.
- Input bytes: `{"sv":"gv-05/1","deps":[["fixture.tz","1"]],"w":"none","in":"2025-03-30T02:30:00","rule":"disambiguation=reject"}`
- Expected bytes: `INSUFFICIENT_INPUT`
- Derivation: `fixture.tz/1` declares no occurrence for the local value;
  neither adjacent offset may fabricate it.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-06 — DST fold

- Rule: repeated local time uses explicit earlier/later occurrence.
- Semantic/dependency versions: `gv-06/1`; `fixture.tz/1`.
- Input bytes: `{"sv":"gv-06/1","deps":[["fixture.tz","1"]],"w":"none","in":"2025-10-26T02:30:00","rule":"compare_disambiguation"}`
- Expected bytes: `{"earlier_offset":"2025-10-26T00:30:00Z","later_offset":"2025-10-26T01:30:00Z","reject":"INSUFFICIENT_INPUT"}`
- Derivation: the exact dependency supplies two occurrences; the token
  selects one or rejects without consulting host rules.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-07 — Holiday and early close

- Rule: use governed session closes, reject closed date.
- Semantic/dependency versions: `gv-07/1`; `fixture.calendar/1`.
- Input bytes: `{"sv":"gv-07/1","deps":[["fixture.calendar","1"]],"w":"none","in":["2025-07-03","2025-07-04","2025-07-07"],"rule":"session_close"}`
- Expected bytes: `{"2025-07-03":"2025-07-03T17:00:00Z","2025-07-04":"INSUFFICIENT_INPUT","2025-07-07":"2025-07-07T20:00:00Z"}`
- Derivation: the exact calendar fixture, not weekday logic, supplies all
  three results.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-08 — Leap day and alignment

- Rule: civil yearly advancement uses `last_day`; origin is 2024-02-29.
- Semantic/dependency versions: `gv-08/1`; none.
- Input bytes: `{"sv":"gv-08/1","deps":[],"w":"none","in":{"origin":"2024-02-29","periods":"I:2"},"rule":"civil_year,last_day"}`
- Expected bytes: `["2024-02-29","2025-02-28","2026-02-28"]`
- Derivation: February 29 is absent in 2025 and 2026, so the declared
  `last_day` rule selects February 28 at each origin-relative boundary.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-09 — Date-only source time

- Rule: instant window cannot strengthen an M39 date into an instant.
- Semantic/dependency versions: `gv-09/1`; none.
- Input bytes: `{"sv":"gv-09/1","deps":[],"w":"none","in":{"id":"O1","precision":"date","time":"2025-01-01"},"rule":"required_precision=instant"}`
- Expected bytes: `INSUFFICIENT_INPUT`
- Derivation: midnight, noon, and session close are all undeclared
  fabrications; the source remains date-only.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-10 — Semantic ordering permutation

- Rule: order by role, complete temporal coordinate, Observation Identity.
- Semantic/dependency versions: `gv-10/1`; none.
- Input bytes: `{"sv":"gv-10/1","deps":[],"w":"none","in":{"manifest_a":["O2","O1","O3"],"manifest_b":["O3","O2","O1"],"observations":[["O1","r","2025-01-01T00:00:00Z"],["O2","r","2025-01-01T00:00:00Z"],["O3","r","2025-01-02T00:00:00Z"]]},"rule":"semantic_order"}`
- Expected bytes: `{"manifest_a_unchanged":["O2","O1","O3"],"manifest_b_unchanged":["O3","O2","O1"],"semantic_order":["O1","O2","O3"]}`
- Derivation: equal temporal coordinates tie-break by `O1 < O2`; later `O3`
  follows. Neither supplied presentation is rewritten.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-11 — Boundary missing data

- Rule: interpolation permits interior gaps only.
- Semantic/dependency versions: `gv-11/1`; none.
- Input bytes: `{"sv":"gv-11/1","deps":[],"w":"none","in":{"expected":["I:0","I:1","I:2"],"present":[["I:1","D:10E0"],["I:2","D:20E0"]]},"rule":"interpolate,max_gap=I:1"}`
- Expected bytes: `INSUFFICIENT_INPUT`
- Derivation: expected position zero is a boundary gap and has no two
  bounding endpoints.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-12 — Interior gap and density

- Rule: exact density `R:2/3`, maximum interior gap one.
- Semantic/dependency versions: `gv-12/1`; none.
- Input bytes: `{"sv":"gv-12/1","deps":[],"w":"none","in":{"expected":["I:0","I:1","I:2"],"present":["I:0","I:2"]},"rule":"exact_density=R:2/3,max_gap=I:1"}`
- Expected bytes: `{"density":"R:2/3","gap":["I:1"],"status":"conforming"}`
- Derivation: two of three positions are present and the sole consecutive
  missing run has length one.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-13 — Prohibited fill

- Rule: role declares `reject`; no fill rule exists.
- Semantic/dependency versions: `gv-13/1`; none.
- Input bytes: `{"sv":"gv-13/1","deps":[],"w":"none","in":{"expected":["I:0","I:1"],"present":[["I:0","D:5E0"]]},"rule":"reject"}`
- Expected bytes: `INSUFFICIENT_INPUT`
- Derivation: forward-fill, zero-fill, and nearest-value results are
  undeclared and therefore cannot satisfy position one.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-14 — Exact interpolation

- Rule: linear interpolation, exact rational arithmetic, no intermediate
  rounding.
- Semantic/dependency versions: `gv-14/1`; none.
- Input bytes: `{"sv":"gv-14/1","deps":[],"w":"none","in":{"t":"I:1","t0":"I:0","t1":"I:3","x0":"D:1E0","x1":"D:2E0"},"rule":"linear,output_scale=2,half_even"}`
- Expected bytes: `D:133E-2`
- Derivation: `1+(2-1)*(1-0)/(3-0)=R:4/3`; quantization to 0.01 half-even
  gives 1.33. No Observation is created.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-15 — Compatible unit

- Rule: add equal unit, scale, basis, and currency.
- Semantic/dependency versions: `gv-15/1`; none.
- Input bytes: `{"sv":"gv-15/1","deps":[],"w":"none","in":[["D:125E-2","m","R:1/1","raw","not_applicable"],["D:275E-2","m","R:1/1","raw","not_applicable"]],"rule":"add"}`
- Expected bytes: `D:4E0`
- Derivation: qualifications are equal; exact sum is 1.25 + 2.75 = 4.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-16 — Incompatible unit

- Rule: addition requires compatible dimensions.
- Semantic/dependency versions: `gv-16/1`; none.
- Input bytes: `{"sv":"gv-16/1","deps":[],"w":"none","in":[["D:1E0","m"],["D:1E0","s"]],"rule":"add"}`
- Expected bytes: `INSUFFICIENT_INPUT`
- Derivation: length and time factor/exponent sequences differ and no
  normalization can make them compatible.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-17 — Unit normalization dependency

- Rule: normalize centimetres to metres before addition.
- Semantic/dependency versions: `gv-17/1`; `fixture.unit/1`.
- Input bytes: `{"sv":"gv-17/1","deps":[["fixture.unit","1"]],"w":"none","in":[["D:1E2","cm"],["D:1E0","m"]],"rule":"normalize_then_add"}`
- Expected bytes: `D:2E0`
- Derivation: dependency factor `R:1/100` makes 100 cm exactly 1 m; adding
  1 m gives 2 m.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-18 — Missing currency

- Rule: currency-meaningful addition requires explicit equal currency.
- Semantic/dependency versions: `gv-18/1`; none.
- Input bytes: `{"sv":"gv-18/1","deps":[],"w":"none","in":[["D:1E1","currency","USD"],["D:2E1","currency","missing"]],"rule":"add"}`
- Expected bytes: `INSUFFICIENT_INPUT`
- Derivation: no Registry, provider, Asset, or peer Observation may fill the
  second currency.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-19 — Multi-currency

- Rule: direct currency addition is not currency-invariant and WP3 has no
  FX authority.
- Semantic/dependency versions: `gv-19/1`; none.
- Input bytes: `{"sv":"gv-19/1","deps":[],"w":"none","in":[["D:1E2","currency","USD"],["D:1E2","currency","EUR"]],"rule":"add"}`
- Expected bytes: `INSUFFICIENT_INPUT`
- Derivation: explicit but unequal currencies are incompatible; no base
  currency or rate may be inferred.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-20 — Raw versus adjusted

- Rule: role accepts `source_adjusted`; transformation is not declared.
- Semantic/dependency versions: `gv-20/1`; none.
- Input bytes: `{"sv":"gv-20/1","deps":[],"w":"none","in":{"basis":"raw","value":"D:1E2"},"rule":"accepted_basis=source_adjusted"}`
- Expected bytes: `INSUFFICIENT_INPUT`
- Derivation: numeric availability does not repair the basis mismatch and
  no silent adjustment is authorized.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-21 — Explicit adjustment

- Rule: event `E1`, dependency factor, multiply before 2025-01-03, exact
  arithmetic.
- Semantic/dependency versions: `gv-21/1`; `fixture.adjust/1`.
- Input bytes: `{"sv":"gv-21/1","deps":[["fixture.adjust","1"]],"w":"none","in":[["2025-01-02","D:1E2","raw"],["2025-01-03","D:6E1","raw"]],"rule":"E1,multiply_prior_by_R:1/2"}`
- Expected bytes: `[["2025-01-02","D:5E1","calculation_normalized"],["2025-01-03","D:6E1","calculation_normalized"]]`
- Derivation: 100 × 1/2 = 50 before the applicability boundary; 60 at the
  boundary is unchanged. No rounding or Observation mutation occurs.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-22 — Decimal tie

- Rule: output scale two, `half_even`.
- Semantic/dependency versions: `gv-22/1`; none.
- Input bytes: `{"sv":"gv-22/1","deps":[],"w":"none","in":["D:1005E-3","D:1015E-3"],"rule":"quantize_scale=2,half_even"}`
- Expected bytes: `["D:1E0","D:102E-2"]`
- Derivation: 1.005 ties between 1.00 and 1.01 and selects even 100; 1.015
  ties between 1.01 and 1.02 and selects even 102.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-23 — Intermediate rounding

- Rule: divide each input by three, add exactly, then one final scale-two
  half-even quantization; intermediate rounding prohibited.
- Semantic/dependency versions: `gv-23/1`; none.
- Input bytes: `{"sv":"gv-23/1","deps":[],"w":"none","in":["D:1E0","D:1E0"],"rule":"(x/3)+(y/3),final_scale=2,half_even"}`
- Expected bytes: `D:67E-2`
- Derivation: exact result is `R:2/3`, producing 0.67. Rounding each third
  first would produce 0.66 and is non-conforming.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-24 — Negative zero

- Rule: supplied negative zero rejected; calculated zero normalized.
- Semantic/dependency versions: `gv-24/1`; none.
- Input bytes: `{"sv":"gv-24/1","deps":[],"w":"none","in":{"calculated":["D:-1E0","D:1E0"],"supplied":"D:-0E0"},"rule":"zero"}`
- Expected bytes: `{"calculated":"D:0E0","supplied":"INSUFFICIENT_INPUT"}`
- Derivation: exact sum is zero and has one canonical decimal encoding;
  `D:-0E0` violates §2.2.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-25 — NaN and infinity

- Rule: exceptional supplied numbers are outside the canonical domain.
- Semantic/dependency versions: `gv-25/1`; none.
- Input bytes: `{"sv":"gv-25/1","deps":[],"w":"none","in":["NaN","+Infinity","-Infinity"],"rule":"parse_numeric"}`
- Expected bytes: `["INSUFFICIENT_INPUT","INSUFFICIENT_INPUT","INSUFFICIENT_INPUT"]`
- Derivation: none matches an integer, decimal, or rational canonical
  lexical form; none can reach successful arithmetic output.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-26 — Divide by zero

- Rule: inputs are valid and sufficient; division occurs in arithmetic.
- Semantic/dependency versions: `gv-26/1`; none.
- Input bytes: `{"sv":"gv-26/1","deps":[],"w":"none","in":["D:1E0","D:0E0"],"rule":"divide"}`
- Expected bytes: `FAILED`
- Derivation: the denominator is a valid supplied decimal, so this is not
  input insufficiency; exact division by zero does not complete.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-27 — Dependency unresolved

- Rule: exact declared dependency version must resolve.
- Semantic/dependency versions: `gv-27/1`; declared
  `fixture.calendar/404`.
- Input bytes: `{"sv":"gv-27/1","deps":[["fixture.calendar","404"]],"w":"none","in":"dependency_absent","rule":"resolve_exact"}`
- Expected bytes: `DEPENDENCY_UNRESOLVED`
- Derivation: the required exact version has no resolving semantic
  authority; weekday or another version cannot substitute.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-28 — Dependency version change

- Rule: same values, exact normalization version changes Method Version
  identity and output.
- Semantic/dependency versions: `gv-28/1` with `fixture.unit/1`;
  `gv-28/2` with `fixture.unit/2`.
- Input bytes: `{"sv":["gv-28/1","gv-28/2"],"deps":[[["fixture.unit","1"]],[["fixture.unit","2"]]],"w":"none","in":["D:1E2","cm"],"rule":"normalize_to_m"}`
- Expected bytes: `{"gv-28/1":"D:1E0","gv-28/2":"D:1E1","method_version_identity_equal":false}`
- Derivation: 100 × 1/100 = 1 under version 1; 100 × 1/10 = 10 under
  version 2. The dependency-list change necessarily changes frozen WP1
  Method Version identity.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-29 — Non-commutative pipeline

- Rule: adjust, then unit-normalize, then interpolate, then arithmetic;
  adjustment applies only to witnessed pre-boundary values.
- Semantic/dependency versions: `gv-29/1`; `fixture.adjust/1`,
  `fixture.unit/1`, ordered by code point.
- Input bytes: `{"sv":"gv-29/1","deps":[["fixture.adjust","1"],["fixture.unit","1"]],"w":"none","in":[["I:0","D:1E2","cm","raw"],["I:2","D:1E2","cm","raw"]],"rule":"adjust_t0_by_R:1/2;normalize_cm_to_m;interpolate_t1;sum"}`
- Expected bytes: `D:225E-2`
- Derivation: adjustment gives 50 cm and 100 cm; normalization gives 0.5 m
  and 1 m; interpolation gives 0.75 m; sum is 2.25 m. Interpolating first
  and then adjusting all pre-boundary working positions would give 2.00 m,
  proving order is semantic.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

### GV-30 — Cross-platform canonical bytes

- Rule: canonical window round trip, exact dependency order, exact rational
  arithmetic, one final scale-six half-even quantization.
- Semantic/dependency versions: `gv-30/1`; `fixture.adjust/1`,
  `fixture.unit/1`, ordered by code point.
- Input bytes: `{"sv":"gv-30/1","deps":[["fixture.adjust","1"],["fixture.unit","1"]],"w":"{\"schema_version\":\"m41-wp3.measurement-window/1\",\"window_kind\":\"elapsed\",\"manifest_identity\":\"hex:4f494d310000000f4d5342310100000001410000000172000000010000000171000000034f3330\",\"start\":{\"precision\":\"instant\",\"value\":\"2025-01-01T00:00:00Z\",\"disambiguation\":\"not_applicable\"},\"start_edge\":\"inclusive\",\"cutoff\":{\"precision\":\"instant\",\"value\":\"2025-01-02T00:00:00Z\",\"disambiguation\":\"not_applicable\"},\"cutoff_edge\":\"inclusive\",\"time_basis\":\"elapsed\",\"timezone_ref\":{\"kind\":\"utc\",\"identifier\":\"UTC\",\"version\":\"fixed\"},\"calendar_ref\":{\"kind\":\"none\",\"identifier\":\"none\",\"version\":\"none\"},\"count\":\"I:0\"}","in":["D:1E0","D:3E0"],"rule":"divide,final_scale=6,half_even"}`
- Expected bytes: `D:333333E-6`
- Derivation: independent decoding reconstructs the exact window and list
  order; exact division is `R:1/3`; scale-six half-even produces 0.333333.
  UTF-8 bytes are hexadecimal
  `44 3a 33 33 33 33 33 33 45 2d 36` on every platform.
- Non-production statement: this fixture admits no production Definition,
  Method Version, formula, or method.

---

## 17. Golden-vector coverage and round-trip evidence

| Component | Covered by |
|---|---|
| A — Measurement Window | GV-01, GV-04, GV-30 |
| B — cutoff, selection, ordering | GV-01, GV-02, GV-09, GV-10 |
| C — timezone, calendar, DST, alignment | GV-03–GV-08 |
| D — missing data and density | GV-11–GV-14 |
| E — units and currency | GV-15–GV-19 |
| F — adjustment and basis | GV-20, GV-21, GV-29 |
| G — arithmetic | GV-14, GV-21–GV-26, GV-29, GV-30 |
| H — dependencies | GV-17, GV-21, GV-27, GV-28, GV-30 |
| I — order and classification | GV-16, GV-25–GV-27, GV-29, GV-30 |

`GV-01`, `GV-04`, and `GV-30` prove that canonical Measurement Window bytes
reconstruct one logical record and re-encode identically without ambient
state. `GV-14`, `GV-21`–`GV-24`, `GV-29`, and `GV-30` prove exact rational
reconstruction, declared quantization only, negative-zero closure, and
byte-identical numeric encoding. `GV-27`–`GV-30` prove exact dependency
closure and identity sensitivity.

Every architecture-required vector row appears exactly once as `GV-01`
through `GV-30`; shared component coverage does not merge or omit a risk.

---

## 18. Canonical determinism requirements

A future semantic specification conforms to Stage B only if an independent
reviewer, using solely:

- frozen WP1/WP2 identities and canonical bytes;
- exact M39 Observation evidence;
- the canonical Measurement Window;
- explicit invocation parameters;
- the exact Method Version semantic version;
- the exact declared dependency identifiers, versions, and canonical
  semantic material; and
- this arithmetic and processing contract

can reconstruct the same selected identities, ordering, working rational
values, classifications, and final canonical arithmetic octets.

Host clock, timezone, locale, library, processor, map order, provider order,
retrieval time, network state, mutable configuration, and presentation are
not inputs. If any output-affecting choice is absent from the permitted
inputs above, the semantic specification is not closed and cannot conform.

---

## 19. Acceptance checklist and final status

| Stage B obligation | Evidence | Status |
|---|---|---|
| Measurement Window record, identity, serialization, validation, errors | §§2–3 | Complete |
| temporal selection/order, inclusive cutoff, intervals, qualified time | §4 | Complete |
| timezone/calendar, alignment, DST, leap/session behavior | §5 | Complete |
| missing data, density, duplicates, interpolation | §6 | Complete |
| unit/currency compatibility and normalization | §7 | Complete |
| adjustment and basis | §8 | Complete |
| exact arithmetic and canonical numeric encoding | §§2, 9 | Complete |
| governed dependency closure | §10 | Complete |
| one cross-dimension processing order | §11, GV-29 | Complete |
| total frozen-outcome classification | §12 | Complete |
| field-level five-part gate | §13 | Pass |
| M34/M39/M40/WP1/WP2/WP4 compatibility | §14 | Complete |
| exact `GV-01` through `GV-30` | §§15–17 | Complete |
| round-trip and cross-platform evidence | §§17–18, GV-30 | Complete |
| no ambient semantic default | §§1.4, 3–12, 18 | Complete |
| implementation/production/operational authority remains none | header, §§1.3, 15 | Preserved |

**Stage B authoring status:** **COMPLETE**.

This status records completion of the specification artifact only. It does
not claim independent approval, does not begin independent review, and does
not change the frozen status of any upstream authority.
